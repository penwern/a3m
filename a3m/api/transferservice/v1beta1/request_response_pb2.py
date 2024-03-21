# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: a3m/api/transferservice/v1beta1/request_response.proto
"""Generated protocol buffer code."""

from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import timestamp_pb2 as google_dot_protobuf_dot_timestamp__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n6a3m/api/transferservice/v1beta1/request_response.proto\x12\x1f\x61\x33m.api.transferservice.v1beta1\x1a\x1fgoogle/protobuf/timestamp.proto"\x80\x01\n\rSubmitRequest\x12\x12\n\x04name\x18\x01 \x01(\tR\x04name\x12\x10\n\x03url\x18\x02 \x01(\tR\x03url\x12I\n\x06\x63onfig\x18\x03 \x01(\x0b\x32\x31.a3m.api.transferservice.v1beta1.ProcessingConfigR\x06\x63onfig" \n\x0eSubmitResponse\x12\x0e\n\x02id\x18\x01 \x01(\tR\x02id"\x1d\n\x0bReadRequest\x12\x0e\n\x02id\x18\x01 \x01(\tR\x02id"\xa2\x01\n\x0cReadResponse\x12\x46\n\x06status\x18\x01 \x01(\x0e\x32..a3m.api.transferservice.v1beta1.PackageStatusR\x06status\x12\x10\n\x03job\x18\x02 \x01(\tR\x03job\x12\x38\n\x04jobs\x18\x03 \x03(\x0b\x32$.a3m.api.transferservice.v1beta1.JobR\x04jobs")\n\x10ListTasksRequest\x12\x15\n\x06job_id\x18\x01 \x01(\tR\x05jobId"P\n\x11ListTasksResponse\x12;\n\x05tasks\x18\x01 \x03(\x0b\x32%.a3m.api.transferservice.v1beta1.TaskR\x05tasks"\x0e\n\x0c\x45mptyRequest"\x0f\n\rEmptyResponse"\xb9\x02\n\x03Job\x12\x0e\n\x02id\x18\x01 \x01(\tR\x02id\x12\x12\n\x04name\x18\x02 \x01(\tR\x04name\x12\x14\n\x05group\x18\x03 \x01(\tR\x05group\x12\x17\n\x07link_id\x18\x04 \x01(\tR\x06linkId\x12\x43\n\x06status\x18\x05 \x01(\x0e\x32+.a3m.api.transferservice.v1beta1.Job.StatusR\x06status\x12\x39\n\nstart_time\x18\x06 \x01(\x0b\x32\x1a.google.protobuf.TimestampR\tstartTime"_\n\x06Status\x12\x16\n\x12STATUS_UNSPECIFIED\x10\x00\x12\x13\n\x0fSTATUS_COMPLETE\x10\x01\x12\x15\n\x11STATUS_PROCESSING\x10\x02\x12\x11\n\rSTATUS_FAILED\x10\x03"\xc6\x02\n\x04Task\x12\x0e\n\x02id\x18\x01 \x01(\tR\x02id\x12\x17\n\x07\x66ile_id\x18\x02 \x01(\tR\x06\x66ileId\x12\x1b\n\texit_code\x18\x03 \x01(\x05R\x08\x65xitCode\x12\x1a\n\x08\x66ilename\x18\x04 \x01(\tR\x08\x66ilename\x12\x1c\n\texecution\x18\x05 \x01(\tR\texecution\x12\x1c\n\targuments\x18\x06 \x01(\tR\targuments\x12\x16\n\x06stdout\x18\x07 \x01(\tR\x06stdout\x12\x16\n\x06stderr\x18\x08 \x01(\tR\x06stderr\x12\x39\n\nstart_time\x18\t \x01(\x0b\x32\x1a.google.protobuf.TimestampR\tstartTime\x12\x35\n\x08\x65nd_time\x18\n \x01(\x0b\x32\x1a.google.protobuf.TimestampR\x07\x65ndTime"\xcc\n\n\x10ProcessingConfig\x12=\n\x1b\x61ssign_uuids_to_directories\x18\x01 \x01(\x08R\x18\x61ssignUuidsToDirectories\x12)\n\x10\x65xamine_contents\x18\x02 \x01(\x08R\x0f\x65xamineContents\x12K\n"generate_transfer_structure_report\x18\x03 \x01(\x08R\x1fgenerateTransferStructureReport\x12<\n\x1a\x64ocument_empty_directories\x18\x04 \x01(\x08R\x18\x64ocumentEmptyDirectories\x12)\n\x10\x65xtract_packages\x18\x05 \x01(\x08R\x0f\x65xtractPackages\x12G\n delete_packages_after_extraction\x18\x06 \x01(\x08R\x1d\x64\x65letePackagesAfterExtraction\x12+\n\x11identify_transfer\x18\x07 \x01(\x08R\x10identifyTransfer\x12G\n identify_submission_and_metadata\x18\x08 \x01(\x08R\x1didentifySubmissionAndMetadata\x12\x42\n\x1didentify_before_normalization\x18\t \x01(\x08R\x1bidentifyBeforeNormalization\x12\x1c\n\tnormalize\x18\n \x01(\x08R\tnormalize\x12)\n\x10transcribe_files\x18\x0b \x01(\x08R\x0ftranscribeFiles\x12J\n"perform_policy_checks_on_originals\x18\x0c \x01(\x08R\x1eperformPolicyChecksOnOriginals\x12g\n1perform_policy_checks_on_preservation_derivatives\x18\r \x01(\x08R,performPolicyChecksOnPreservationDerivatives\x12\x32\n\x15\x61ip_compression_level\x18\x0e \x01(\x05R\x13\x61ipCompressionLevel\x12\x85\x01\n\x19\x61ip_compression_algorithm\x18\x0f \x01(\x0e\x32I.a3m.api.transferservice.v1beta1.ProcessingConfig.AIPCompressionAlgorithmR\x17\x61ipCompressionAlgorithm"\xda\x02\n\x17\x41IPCompressionAlgorithm\x12)\n%AIP_COMPRESSION_ALGORITHM_UNSPECIFIED\x10\x00\x12*\n&AIP_COMPRESSION_ALGORITHM_UNCOMPRESSED\x10\x01\x12!\n\x1d\x41IP_COMPRESSION_ALGORITHM_TAR\x10\x02\x12\'\n#AIP_COMPRESSION_ALGORITHM_TAR_BZIP2\x10\x03\x12&\n"AIP_COMPRESSION_ALGORITHM_TAR_GZIP\x10\x04\x12%\n!AIP_COMPRESSION_ALGORITHM_S7_COPY\x10\x05\x12&\n"AIP_COMPRESSION_ALGORITHM_S7_BZIP2\x10\x06\x12%\n!AIP_COMPRESSION_ALGORITHM_S7_LZMA\x10\x07*\xa3\x01\n\rPackageStatus\x12\x1e\n\x1aPACKAGE_STATUS_UNSPECIFIED\x10\x00\x12\x19\n\x15PACKAGE_STATUS_FAILED\x10\x01\x12\x1b\n\x17PACKAGE_STATUS_REJECTED\x10\x02\x12\x1b\n\x17PACKAGE_STATUS_COMPLETE\x10\x03\x12\x1d\n\x19PACKAGE_STATUS_PROCESSING\x10\x04\x42\xb1\x02\n#com.a3m.api.transferservice.v1beta1B\x14RequestResponseProtoP\x01ZUgithub.com/artefactual-labs/a3m/proto/a3m/api/transferservice/v1beta1;transferservice\xa2\x02\x03\x41\x41T\xaa\x02\x1f\x41\x33m.Api.Transferservice.V1beta1\xca\x02\x1f\x41\x33m\\Api\\Transferservice\\V1beta1\xe2\x02+A3m\\Api\\Transferservice\\V1beta1\\GPBMetadata\xea\x02"A3m::Api::Transferservice::V1beta1b\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(
    DESCRIPTOR, "a3m.api.transferservice.v1beta1.request_response_pb2", _globals
)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    DESCRIPTOR._serialized_options = b'\n#com.a3m.api.transferservice.v1beta1B\024RequestResponseProtoP\001ZUgithub.com/artefactual-labs/a3m/proto/a3m/api/transferservice/v1beta1;transferservice\242\002\003AAT\252\002\037A3m.Api.Transferservice.V1beta1\312\002\037A3m\\Api\\Transferservice\\V1beta1\342\002+A3m\\Api\\Transferservice\\V1beta1\\GPBMetadata\352\002"A3m::Api::Transferservice::V1beta1'
    _globals["_PACKAGESTATUS"]._serialized_start = 2648
    _globals["_PACKAGESTATUS"]._serialized_end = 2811
    _globals["_SUBMITREQUEST"]._serialized_start = 125
    _globals["_SUBMITREQUEST"]._serialized_end = 253
    _globals["_SUBMITRESPONSE"]._serialized_start = 255
    _globals["_SUBMITRESPONSE"]._serialized_end = 287
    _globals["_READREQUEST"]._serialized_start = 289
    _globals["_READREQUEST"]._serialized_end = 318
    _globals["_READRESPONSE"]._serialized_start = 321
    _globals["_READRESPONSE"]._serialized_end = 483
    _globals["_LISTTASKSREQUEST"]._serialized_start = 485
    _globals["_LISTTASKSREQUEST"]._serialized_end = 526
    _globals["_LISTTASKSRESPONSE"]._serialized_start = 528
    _globals["_LISTTASKSRESPONSE"]._serialized_end = 608
    _globals["_EMPTYREQUEST"]._serialized_start = 610
    _globals["_EMPTYREQUEST"]._serialized_end = 624
    _globals["_EMPTYRESPONSE"]._serialized_start = 626
    _globals["_EMPTYRESPONSE"]._serialized_end = 641
    _globals["_JOB"]._serialized_start = 644
    _globals["_JOB"]._serialized_end = 957
    _globals["_JOB_STATUS"]._serialized_start = 862
    _globals["_JOB_STATUS"]._serialized_end = 957
    _globals["_TASK"]._serialized_start = 960
    _globals["_TASK"]._serialized_end = 1286
    _globals["_PROCESSINGCONFIG"]._serialized_start = 1289
    _globals["_PROCESSINGCONFIG"]._serialized_end = 2645
    _globals["_PROCESSINGCONFIG_AIPCOMPRESSIONALGORITHM"]._serialized_start = 2299
    _globals["_PROCESSINGCONFIG_AIPCOMPRESSIONALGORITHM"]._serialized_end = 2645
# @@protoc_insertion_point(module_scope)
