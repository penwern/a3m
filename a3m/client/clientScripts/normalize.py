import argparse
import csv
import os
import traceback
import uuid

from django.db import transaction
from django.utils import timezone

from a3m import databaseFunctions
from a3m import fileOperations
from a3m.dicts import ReplacementDict
from a3m.dicts import setup_dicts
from a3m.executeOrRunSubProcess import executeOrRun
from a3m.fpr.registry import FPR
from a3m.fpr.registry import Command
from a3m.fpr.registry import CommandScriptType
from a3m.fpr.registry import JSONBackend
from a3m.fpr.registry import Rule
from a3m.fpr.registry import RulePurpose

# from a3m.fpr.registry import RulePurpose
from a3m.main.models import Derivation
from a3m.main.models import File
from a3m.main.models import FileFormatVersion
from a3m.main.models import FileID

# Return codes
SUCCESS = 0
RULE_FAILED = 1
NO_RULE_FOUND = 2


class Executor:
    """
    Execute normalization commands.

    This class used to be in a module called transcoder, moved here as-is.
    """

    exit_code: int | None

    def __init__(
        self, job, command: Command, replacement_dict, on_success=None, opts=None
    ):
        self.fpcommand = command
        self.command = command.command
        self.type = command.script_type
        self.output_location = command.output_location
        self.replacement_dict = replacement_dict
        self.on_success = on_success
        self.std_out = ""
        self.exit_code = None
        self.opts = opts
        self.job = job

        # Add the output location to the replacement dict - for use in
        # verification and event detail commands
        if self.output_location:
            self.output_location = self.replacement_dict.replace(self.output_location)[
                0
            ]
            self.replacement_dict["%outputLocation%"] = self.output_location

        # Add verification and event detail commands, if they exist
        self.verification_command = None
        if self.fpcommand.verification_command:
            self.verification_command = Executor(
                self.job, self.fpcommand.verification_command, self.replacement_dict
            )

        self.event_detail_command = None
        if self.fpcommand.event_detail_command:
            self.event_detail_command = Executor(
                self.job, self.fpcommand.event_detail_command, self.replacement_dict
            )

    def __str__(self):
        return "[COMMAND] {}\n\tExecuting: {}\n\tOutput location: {}\n".format(
            self.fpcommand, self.command, self.output_location
        )

    def execute(self, skip_on_success=False):
        """Execute the the command, and associated verification and event detail commands.

        Returns 0 if all commands succeeded, non-0 if any failed."""
        # For "command" and "bashScript" type delegate tools, e.g.
        # individual commandline statements or bash scripts, we interpolate
        # the necessary values into the script's source
        args = []
        if self.type in [CommandScriptType.COMMAND, CommandScriptType.BASH_SCRIPT]:
            self.command = self.replacement_dict.replace(self.command)[0]
        # For other command types, we translate the entries from
        # replacement_dict into GNU-style long options, e.g.
        # [%fileName%, foo] => --file-name=foo
        else:
            args = self.replacement_dict.to_gnu_options()
        self.job.print_output("Command to execute:", self.command)
        self.job.print_output("-----")
        self.job.print_output("Command stdout:")
        self.exit_code, self.std_out, std_err = executeOrRun(
            self.type, self.command, arguments=args, capture_output=True
        )
        self.job.write_output(self.std_out)
        self.job.write_error(std_err)
        self.job.print_output("-----")
        self.job.print_output("Command exit code:", self.exit_code)
        if self.exit_code == 0 and self.verification_command:
            self.job.print_output(
                "Running verification command", self.verification_command
            )
            self.job.print_output("-----")
            self.job.print_output("Command stdout:")
            self.exit_code = self.verification_command.execute(skip_on_success=True)
            self.job.print_output("-----")
            self.job.print_output("Verification Command exit code:", self.exit_code)

        if self.exit_code == 0 and self.event_detail_command:
            self.job.print_output(
                "Running event detail command", self.event_detail_command
            )
            self.event_detail_command.execute(skip_on_success=True)

        # If unsuccesful
        if self.exit_code != 0:
            self.job.print_error("Failed:", self.fpcommand)
            self.job.print_error("Standard out:", self.std_out)
            self.job.print_error("Standard error:", std_err)
        else:
            if (not skip_on_success) and self.on_success:
                self.on_success(self, self.opts, self.replacement_dict)
        return self.exit_code


def get_replacement_dict(job, opts):
    """Generates values for all knows %var% replacement variables."""
    prefix = ""
    postfix = ""
    output_dir = ""
    # get file name and extension
    (directory, basename) = os.path.split(opts.file_path)
    directory += os.path.sep  # All paths should have trailing /
    (filename, _) = os.path.splitext(basename)

    # postfix = "-" + opts.task_uuid
    # output_dir = directory

    if "preservation" in opts.purpose:
        postfix = "-" + opts.task_uuid
        output_dir = directory
    elif "access" in opts.purpose:
        prefix = opts.file_uuid + "-"
        output_dir = os.path.join(opts.sip_path, "DIP", "objects") + os.path.sep
    elif "thumbnail" in opts.purpose:
        output_dir = os.path.join(opts.sip_path, "thumbnails") + os.path.sep
        postfix = opts.file_uuid
    else:
        job.print_error("Unsupported command purpose", opts.purpose)
        return None

    # Populates the standard set of unit variables, so,
    # e.g., %fileUUID% is available
    replacement_dict = ReplacementDict.frommodel(type_="file", file_=opts.file_uuid)

    output_filename = "".join([prefix, filename, postfix])
    replacement_dict.update(
        {
            "%outputDirectory%": output_dir,
            "%prefix%": prefix,
            "%postfix%": postfix,
            "%outputFileName%": output_filename,  # does not include extension
            "%outputFilePath%": os.path.join(
                output_dir, output_filename
            ),  # does not include extension
        }
    )
    return replacement_dict


def check_manual_normalization(job, opts):
    """Checks for manually normalized file, returns that path or None.

    Checks by looking for access/preservation files for a give original file.

    Check the manualNormalization/access and manualNormalization/preservation
    directories for access and preservation files.  If a nomalization.csv
    file is specified, check there first for the mapping between original
    file and access/preservation file."""

    # If normalization.csv provided, check there for mapping from original
    # to access/preservation file
    normalization_csv = os.path.join(
        opts.sip_path, "objects", "manualNormalization", "normalization.csv"
    )
    # Get original name of target file, to handle changed names
    file_ = File.objects.get(uuid=opts.file_uuid)
    bname = file_.originallocation.replace(
        "%transferDirectory%objects/", "", 1
    ).replace("%SIPDirectory%objects/", "", 1)
    if os.path.isfile(normalization_csv):
        found = False
        access_file = None
        preservation_file = None
        # use universal newline mode to support unusual newlines, like \r
        with open(normalization_csv) as csv_file:
            reader = csv.reader(csv_file)
            # Search the file for an original filename that matches the one provided
            try:
                for row in reader:
                    if not row:
                        continue
                    if "#" in row[0]:  # ignore comments
                        continue
                    original, access_file, preservation_file = row
                    if original == bname:
                        job.print_output(
                            "Filename",
                            bname,
                            "matches entry in normalization.csv",
                            original,
                        )
                        found = True
                        break
            except csv.Error:
                job.print_error(
                    "Error reading", normalization_csv, " on line", reader.line_num
                )
                job.print_error(traceback.format_exc())
                return None

        # If we didn't find a match, let it fall through to the usual method
        if found:
            # No manually normalized file for command classification
            if "preservation" in opts.purpose and not preservation_file:
                return None
            if "access" in opts.purpose and not access_file:
                return None

            # If we found a match, verify access/preservation exists in DB
            # match and pull original location b/c filename changes
            if "preservation" in opts.purpose:
                filename = preservation_file
            elif "access" in opts.purpose:
                filename = access_file
            else:
                return None
            job.print_output("Looking for", filename, "in database")
            # FIXME: SQL uses removedtime=0. Convince Django to express this
            return File.objects.get(
                sip=opts.sip_uuid, originallocation__iendswith=filename
            )  # removedtime = 0

    # Assume that any access/preservation file found with the right
    # name is the correct one
    # Strip extension, replace SIP path with %var%
    path = os.path.splitext(opts.file_path.replace(opts.sip_path, "%SIPDirectory%", 1))[
        0
    ]

    if "preservation" in opts.purpose:
        path = path.replace(
            "%SIPDirectory%objects/",
            "%SIPDirectory%objects/manualNormalization/preservation/",
        )
    elif "access" in opts.purpose:
        path = path.replace(
            "%SIPDirectory%objects/",
            "%SIPDirectory%objects/manualNormalization/access/",
        )
    else:
        return None

    # FIXME: SQL uses removedtime=0. Cannot get Django to express this
    job.print_output(
        "Checking for a manually normalized file by trying to get the"
        f" unique file that matches SIP UUID {opts.sip_uuid} and whose currentlocation"
        f" value starts with this path: {path}."
    )
    matches = File.objects.filter(  # removedtime = 0
        sip=opts.sip_uuid, currentlocation__startswith=path
    )
    if not matches:
        # No file with the correct path found, assume not manually normalized
        job.print_output("No such file found.")
        return None
    if len(matches) > 1:
        # If multiple matches, the shortest one should be the correct one. E.g.,
        # if original is /a/b/abc.NEF then /a/b/abc.tif and /a/b/abc_1.tif will
        # both match but /a/b/abc.tif is the correct match.
        job.print_output(
            f"Multiple files matching path {path} found. Returning the shortest one."
        )
        ret = sorted(matches, key=lambda f: f.currentlocation)[0]
        job.print_output(f"Returning file at {ret.currentlocation}")
        return ret
    return matches[0]


def once_normalized(job, executor: Executor, opts, replacement_dict):
    """Updates the database if normalization completed successfully.

    Callback from Executor

    For preservation files, adds a normalization event, and derivation, as well
    as updating the size and checksum for the new file in the DB.  Adds format
    information for use in the METS file to FilesIDs.
    """
    transcoded_files = []
    if not executor.output_location:
        executor.output_location = ""
    if os.path.isfile(executor.output_location):
        transcoded_files.append(executor.output_location)
    elif os.path.isdir(executor.output_location):
        for w in os.walk(executor.output_location):
            path, _, files = w
            for p in files:
                p = os.path.join(path, p)
                if os.path.isfile(p):
                    transcoded_files.append(p)
    elif executor.output_location:
        job.print_error(
            "Error - output file does not exist [", executor.output_location, "]"
        )
        executor.exit_code = -2

    derivation_event_uuid = str(uuid.uuid4())
    event_detail_output = f'ArchivematicaFPRCommandID="{executor.fpcommand.id}"'
    if executor.event_detail_command is not None:
        event_detail_output += f"; {executor.event_detail_command.std_out}"
    for ef in transcoded_files:
        if "thumbnails" in opts.purpose:
            continue
        today = timezone.now()
        output_file_uuid = opts.task_uuid  # Match the UUID on disk
        # TODO Add manual normalization for files of same name mapping?
        # Add the new file to the SIP
        path_relative_to_sip = ef.replace(opts.sip_path, "%SIPDirectory%", 1)
        fileOperations.addFileToSIP(
            path_relative_to_sip,
            output_file_uuid,  # File UUID
            opts.sip_uuid,  # SIP UUID
            opts.task_uuid,  # Task UUID
            today,  # Current date
            sourceType="creation",
            use=opts.purpose,
        )

        # Calculate new file checksum
        fileOperations.updateSizeAndChecksum(
            output_file_uuid,  # File UUID, same as task UUID for preservation
            ef,  # File path
            today,  # Date
            str(uuid.uuid4()),  # Event UUID, new UUID
        )

        # Add derivation link and associated event
        #
        # Track both events and insert into Derivations table for
        # preservation copies
        if "preservation" in opts.purpose:
            insert_derivation_event(
                original_uuid=opts.file_uuid,
                output_uuid=output_file_uuid,
                derivation_uuid=derivation_event_uuid,
                event_detail_output=event_detail_output,
                outcome_detail_note=path_relative_to_sip,
                today=today,
            )

        # Other derivatives go into the Derivations table, but
        # don't get added to the PREMIS Events because they will
        # not appear in the METS.
        else:
            d = Derivation(
                source_file_id=opts.file_uuid,
                derived_file_id=output_file_uuid,
                event=None,
            )
            d.save()

        if executor.fpcommand.output_format is None:
            job.print_error("Error - command output format is undefined.")
            executor.exit_code = -2
            return

        # Use the format info from the normalization command
        # to save identification into the DB
        FileFormatVersion.objects.create(
            file_uuid_id=output_file_uuid,
            format_version_id=executor.fpcommand.output_format.id,
        )
        FileID.objects.create(
            file_id=output_file_uuid,
            format_name=executor.fpcommand.output_format.format.description,
        )


def once_normalized_callback(job):
    def wrapper(*args):
        return once_normalized(job, *args)

    return wrapper


def insert_derivation_event(
    original_uuid,
    output_uuid,
    derivation_uuid,
    event_detail_output,
    outcome_detail_note,
    today=None,
):
    """Add the derivation link for preservation files and the event."""
    if today is None:
        today = timezone.now()
    # Add event information to current file
    databaseFunctions.insertIntoEvents(
        fileUUID=original_uuid,
        eventIdentifierUUID=derivation_uuid,
        eventType="normalization",
        eventDateTime=today,
        eventDetail=event_detail_output,
        eventOutcome="",
        eventOutcomeDetailNote=outcome_detail_note or "",
    )

    # Add linking information between files
    databaseFunctions.insertIntoDerivations(
        sourceFileUUID=original_uuid,
        derivedFileUUID=output_uuid,
        relatedEventUUID=derivation_uuid,
    )


def get_default_rule(purpose) -> Rule | None:
    """Get the default rule for a given purpose."""

    # Convert purpose to default_purpose
    try:
        default_purpose = RulePurpose(f"default_{purpose}")
    except ValueError:
        return None

    # Get all rules for this default purpose
    rules = []
    # Type check to ensure we're working with JSONBackend
    if isinstance(FPR.backend, JSONBackend):
        for format_version in FPR.backend.versions.values():
            if (
                format_version.enabled
                and format_version.id not in FPR.backend.replaced_versions
            ):
                format_rules = FPR.backend.get_rules(format_version.id, default_purpose)
                rules.extend(format_rules)

        # Return first enabled rule that isn't replaced
        for rule in rules:
            if rule.enabled and rule.id not in FPR.backend.replaced_rules:
                return rule
    return None


def main(job, opts):
    """Find and execute normalization commands on input file."""
    setup_dicts()

    # Find the file and itss FormatVersion (file identification)
    try:
        file_ = File.objects.get(uuid=opts.file_uuid)
    except File.DoesNotExist:
        job.print_error("File with uuid", opts.file_uuid, "does not exist in database.")
        return NO_RULE_FOUND
    job.print_output("File found:", file_.uuid, file_.currentlocation)

    # Unless normalization file group use is submissionDocumentation, skip the
    # submissionDocumentation directory
    if (
        opts.normalize_file_grp_use != "submissionDocumentation"
        and file_.currentlocation.startswith(
            "%SIPDirectory%objects/submissionDocumentation"
        )
    ):
        job.print_output(
            "File",
            os.path.basename(opts.file_path),
            "in objects/submissionDocumentation, skipping",
        )
        return SUCCESS

    # Only normalize files where the file's group use and normalize group use match
    if file_.filegrpuse != opts.normalize_file_grp_use:
        job.print_output(
            os.path.basename(opts.file_path),
            "is file group usage",
            file_.filegrpuse,
            "instead of ",
            opts.normalize_file_grp_use,
            " - skipping",
        )
        return SUCCESS

    # # For re-ingest: clean up old derivations
    # # If the file already has a Derivation with the same purpose, remove it and mark the derived file as deleted
    # derivatives = Derivation.objects.filter(
    #     source_file=file_, derived_file__filegrpuse=opts.purpose
    # )
    # derivatives_to_delete = []
    # for derivative in derivatives:
    #     derivatives_to_delete.append(derivative.id)
    #     job.print_output(
    #         opts.purpose,
    #         "derivative",
    #         derivative.derived_file_id,
    #         "already exists, marking as deleted",
    #     )
    #     File.objects.filter(uuid=derivative.derived_file_id).update(
    #         filegrpuse="deleted"
    #     )
    #     # Don't create events for thumbnail files
    #     if opts.purpose != "thumbnail":
    #         databaseFunctions.insertIntoEvents(
    #             fileUUID=derivative.derived_file_id, eventType="deletion"
    #         )
    # if derivatives_to_delete:
    #     Derivation.objects.filter(id__in=derivatives_to_delete).delete()

    # If a file has been manually normalized for this purpose, skip it
    manually_normalized_file = check_manual_normalization(job, opts)
    if manually_normalized_file:
        job.print_output(
            os.path.basename(opts.file_path),
            "was already manually normalized into",
            manually_normalized_file.currentlocation,
        )
        if "preservation" in opts.purpose:
            # Add derivation link and associated event
            insert_derivation_event(
                original_uuid=opts.file_uuid,
                output_uuid=manually_normalized_file.uuid,
                derivation_uuid=str(uuid.uuid4()),
                event_detail_output="manual normalization",
                outcome_detail_note=None,
            )
        return SUCCESS

    do_fallback = False
    try:
        file_format_version = FileFormatVersion.objects.get(file_uuid=opts.file_uuid)
    except FileFormatVersion.DoesNotExist:
        file_format_version = None

    # Look up the normalization command in the FPR
    if file_format_version:
        job.print_output("File format:", file_format_version.format_version_id)
        rules = FPR.get_file_rules(file=opts.file_uuid, purpose=opts.purpose)
        if not rules:
            if (
                opts.purpose == "thumbnail"
                and opts.thumbnail_mode == "generate_non_default"
            ):
                job.pyprint("Thumbnail not generated as no rule found for format")
                return SUCCESS
            else:
                do_fallback = True
        else:
            rule = rules[0]

    # Try with default rule if no format_id or rule was found
    if file_format_version is None or do_fallback:
        rule = get_default_rule(opts.purpose)
        if rule:
            job.print_output(
                os.path.basename(file_.currentlocation),
                "not identified or without rule",
                "- Falling back to default",
                opts.purpose,
                "rule",
            )
        else:
            job.print_output(
                "Not normalizing",
                os.path.basename(file_.currentlocation),
                " - No rule or default rule found to normalize for",
                opts.purpose,
            )
            return NO_RULE_FOUND

    job.print_output("Format Policy Rule:", rule.id)
    command = rule.command
    job.print_output("Format Policy Command:", command.description)

    replacement_dict = get_replacement_dict(job, opts)

    cl = Executor(job, command, replacement_dict, once_normalized_callback(job), opts)
    exitstatus = cl.execute()

    # If the access/thumbnail normalization command has errored AND a
    # derivative was NOT created, then we run the default access/thumbnail
    # rule. Note that we DO need to check if the derivative file exists. Even
    # when a verification command exists for the normalization command, the
    # transcoder.py::Command.execute method will only run the verification
    # command if the normalization command returns a 0 exit code.
    # Errored thumbnail normalization also needs to result in default thumbnail
    # normalization; if not, then a transfer with a single file that failed
    # thumbnail normalization will result in a failed SIP at "Prepare DIP: Copy
    # thumbnails to DIP directory"
    if (
        exitstatus != 0
        and opts.purpose in ("access", "thumbnail")
        and cl.output_location
        and (not os.path.isfile(cl.output_location))
    ):
        # Fall back to default rule
        fallback_rule = get_default_rule(opts.purpose)
        if fallback_rule:
            job.print_output(
                opts.purpose,
                "normalization failed, falling back to default",
                opts.purpose,
                "rule",
            )
        else:
            job.print_output(
                "Not retrying normalizing for",
                os.path.basename(file_.currentlocation),
                " - No default rule found to normalize for",
                opts.purpose,
            )
            fallback_rule = None
        # Don't re-run the same command
        if fallback_rule and fallback_rule.command != command:
            job.print_output("Fallback Format Policy Rule:", fallback_rule)
            command = fallback_rule.command
            job.print_output("Fallback Format Policy Command", command.description)

            # Use existing replacement dict
            cl = Executor(
                job,
                # fallback_rule,
                command,
                replacement_dict,
                once_normalized_callback(job),
                opts,
            )
            exitstatus = cl.execute()

    # TODO Needed for thumbnails?
    # # Store thumbnails locally for use during AIP searches
    # # TODO is this still needed, with the storage service?
    # if "thumbnail" in opts.purpose:
    #     thumbnail_filepath = cl.commandObject.output_location
    #     thumbnail_storage_dir = os.path.join(
    #         mcpclient_settings.SHARED_DIRECTORY, "www", "thumbnails", opts.sip_uuid
    #     )
    #     try:
    #         os.makedirs(thumbnail_storage_dir)
    #     except OSError as e:
    #         if e.errno == errno.EEXIST and os.path.isdir(thumbnail_storage_dir):
    #             pass
    #         else:
    #             raise
    #     thumbnail_basename, thumbnail_extension = os.path.splitext(thumbnail_filepath)
    #     thumbnail_storage_file = os.path.join(
    #         thumbnail_storage_dir, opts.file_uuid + thumbnail_extension
    #     )
    #     shutil.copyfile(thumbnail_filepath, thumbnail_storage_file)

    if not exitstatus == 0:
        job.print_error(f"Command {command.description} failed!")
        return RULE_FAILED

    path = os.path.basename(opts.file_path)
    job.print_output(f"Successfully normalized {path} for {opts.purpose}")
    return SUCCESS


def call(jobs):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "purpose", type=str, help='"preservation", "access", "thumbnail"'
    )
    parser.add_argument("file_uuid", type=str, help="%fileUUID%")
    parser.add_argument("file_path", type=str, help="%relativeLocation%")
    parser.add_argument("sip_path", type=str, help="%SIPDirectory%")
    parser.add_argument("sip_uuid", type=str, help="%SIPUUID%")
    parser.add_argument("task_uuid", type=str, help="%taskUUID%")
    parser.add_argument(
        "normalize_file_grp_use",
        type=str,
        help='"service", "original", "submissionDocumentation", etc',
    )
    parser.add_argument(
        "--thumbnail_mode",
        type=str,
        default="generate",
        help='"generate", "generate_non_default", "do_not_generate"',
    )

    with transaction.atomic():
        for job in jobs:
            with job.JobContext():
                opts = parser.parse_args(job.args[1:])

                if (
                    opts.purpose == "thumbnail"
                    and opts.thumbnail_mode == "do_not_generate"
                ):
                    job.print_output("Thumbnail generation has been disabled")
                    job.set_status(SUCCESS)
                    continue

                try:
                    job.set_status(main(job, opts))
                except Exception as e:
                    job.print_error(str(e))
                    job.set_status(1)
