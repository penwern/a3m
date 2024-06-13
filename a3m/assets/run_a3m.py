import py7zr
import docker
import json
import docker.errors
import jsonschema
import re
from pathlib import Path

docker_client = docker.from_env()

def validate_workflow():
    
    with open('/home/cameron/penwern/a3m_penwern/a3m/assets/workflow-schema-v1.json', 'r') as file:
        workflow_schema = json.load(file)
        
    with open('/home/cameron/penwern/a3m_penwern/a3m/assets/workflow.json', 'r') as file:
        workflow_json = json.load(file)

    try:
        jsonschema.validate(instance=workflow_json, schema=workflow_schema)
        print("JSON data valid against the schema.")
    except jsonschema.ValidationError as e:
        raise e
    
def get_last_uuid(log_string):
    pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    uuids = re.findall(pattern, log_string)
    if uuids:
        return uuids[-1]
    else:
        raise ValueError("No UUID found in the log string.")

def build_docker_image():
    try:
        docker_client.images.build(
            path="/home/cameron/penwern/a3m_penwern",
            tag="penwern-a3m"
        )
    except docker.errors.BuildError as e:
        print("Build failed:", e)
    except docker.errors.APIError as e:
        print("Docker API error:", e)
    print("Image build completed.")

def execute_a3m_command():
    
    print("Starting a3m Transfer.")
    
    execute_transfer_command = [
        "-m", "a3m.cli.client",
        "--name=transfer1",
        "file:///tmp/demo/transfers/DemoTransferCSV"
    ]
    
    container = docker_client.containers.run(
        "penwern-a3m",
        execute_transfer_command,
        remove=True,
        tty=True,
        entrypoint='python',
        environment={"A3M_DEBUG": "True"},
        volumes={"/tmp/demo/transfers": {"bind": "/tmp/demo/transfers", "mode": "rw"},
                "/tmp/demo/completed": {"bind": "/home/a3m/.local/share/a3m/share/completed", "mode": "rw"}}
    )

    output = container.decode("utf-8")

    if not output:
        print("No output from the container.")
    
    with open('/home/cameron/penwern/a3m_penwern/a3m/assets/a3m_output.txt', 'w') as file:
        file.write(output)

    print("Transfer Complete.")
    return output

def list_aip_content(directory_path: Path, aip_uuid: str):
    
    files = directory_path.glob('*')
    
    aip_name = ""
    for file in files:
        if file.is_file() and aip_uuid in file.name:
            aip_name = file.name
            
    if not aip_name:
        raise ValueError(f"No AIP file found with UUID {aip_uuid}.")

    aip_path = directory_path / aip_name
    with py7zr.SevenZipFile(aip_path, mode='r') as archive:
        # Get a list of all file names in the archive
        file_names = archive.getnames()
        
        print("AIP Content:")
        for file in file_names:
            print(file)
        return file_names

def parse_a3m_logging(text):

    # Array of strings split by line
    lines = text.split("\n")

    if "Processing completed successfully!" in lines[-3]:
        print(lines[-3])
    else:
        print("A3M Failed")
        
    bounties = ['cmd_mkdir', 'for access', 'for thumbnail', 'remove_files_without_premis_metadata']
        
    bounties_d = {}
        
    for word in bounties:
        bounties_d[word] = text.count(word)
        
    print(bounties_d)
        
    # Define a regular expression pattern to extract relevant information
    pattern = r'^(\w+)\s+<\d+:([^>]+)>\s+<(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})>\s+(\S+):(.+)$'

    # Compile the pattern
    regex = re.compile(pattern, re.MULTILINE)

    # Find all matches in the log entries
    matches = regex.findall(text)
    
    # Iterate over matches and print them
    # for match in matches[:-5]:
    #     print("Level:", match[0])
    #     print("Thread:", match[1])
    #     print("Timestamp:", match[2])
    #     print("Module:", match[3])
    #     print("Message:", match[4])
    #     print()

def main():
    
    validate_workflow()
    build_docker_image()
    
    output = execute_a3m_command()
    parse_a3m_logging(output)
    
    aip_uuid = get_last_uuid(output)
    list_aip_content(Path("/tmp/demo/completed/"), aip_uuid)
    

if __name__ == "__main__":
    main()
