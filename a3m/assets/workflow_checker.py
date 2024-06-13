import json
import re
import jsonschema


with open('/home/cameron/penwern/a3m_penwern/a3m/assets/workflow-schema-v1.json', 'r') as file:
    schema = json.load(file)

def validate_json(data: dict):
    try:
        jsonschema.validate(instance=data, schema=schema)
        print("JSON data is valid against the schema.")
    except jsonschema.ValidationError as e:
        # print(f"JSON data is not valid.")
        # print(f"JSON data is not valid. Error: {e}")
        raise e

def gather_dip_jobs_uuids(attributes: dict, job_id: str):
    """
    Recursive function to collate jobs containing strings containing "DIP"
    """
    dip_job_ids = []
    for val in attributes.values():
        if isinstance(val, str):
            if "DIP" in val:
                dip_job_ids.append(job_id)
        elif isinstance(val, dict):
            dip_job_ids.extend(gather_dip_jobs_uuids(val, job_id))
        elif isinstance(val, list):
            for a in val:
                if isinstance(a, str):
                    if "DIP" in a:
                        dip_job_ids.append(job_id)
                elif isinstance(a, dict):
                    dip_job_ids.extend(gather_dip_jobs_uuids(a, job_id))
    return dip_job_ids

def gather_linking_uuids(data: dict):
    """
    Recursive function to collate linking uuids.
    """
    link_ids = []
    for val in data.values():
        if isinstance(val, str):
            if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", val):
                link_ids.append(val)
        elif isinstance(val, dict):
            link_ids.extend(gather_linking_uuids(val))
        elif isinstance(val, list):
            for a in val:
                if isinstance(a, str):
                    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", a):
                        link_ids.append(a)
                elif isinstance(a, dict):
                    link_ids.extend(gather_linking_uuids(a))
    return link_ids

def check_dict_dead_links(data: dict) -> list[str]:
    job_uuids = []
    linking_uuids = []

    for job, attributes in data['links'].items():
        job_uuids.append(job)
        linking_uuids.extend(gather_linking_uuids(attributes))

    unique_jobs = list(set(job_uuids))
    unique_links = list(set(linking_uuids))
    
    bounties = ['aaebd7d4-5dc5-4579-893e-60650506d1cd']
    found_bounties = [a for a in bounties if a in unique_jobs + unique_links]
    if found_bounties:
        print(f"Bounties: {found_bounties}")
    
    dead_links = [a for a in unique_links if a not in unique_jobs]
    return dead_links
    
def migrate_old_job(data: dict):
    """
    Migrates
    
    Returns false if manager is depreciated
    """
    config = data.get('config')
    depreciated_managers = ['linkTaskManagerSetUnitVariable']
    execute_updates = {
        'createDirectory_v0.0': 'cmd_mkdir',
        'validateFile_v1.0': 'validate_file',
        'normalize_v1.0': 'normalize',
        'manualNormalizationMoveAccessFilesToDIP_v0.0': 'manual_normalization_move_access_files_to_dip',
        'checkForAccessDirectory_v0.0': 'check_for_access_directory',
        'moveSIP_v0.0': 'move_sip',
        'failedSIPCleanup_v1.0': 'failed_sip_cleanup'
    }
    if config:
        # Check depreciated @manager
        if config.get('@manager') in depreciated_managers:
            return False
        
        # Remove @model
        if config.get('@model'):
            config.pop('@model')
            
        # Remove chain_id
        if config.get('chain_id'):
            print(f"DEBUG: Removing chain_id {config['chain_id']}")
            config.pop('chain_id')
            
        # Updating execute
        if config.get('execute'):
            execute_string = config['execute']
            if execute_string in execute_updates.keys():
                config['execute'] = execute_updates[execute_string]
            elif execute_string not in execute_updates.values():
                print(f"WARN: Check Execute Command: {execute_string}")
        # Remove keys with null values
        config = {k: v for k, v in config.items() if v is not None}
        data['config'] = config
    return True

    
def migrate_and_add_jobs(uuid_list: list, data: dict, old_data: dict):
    """
    Recursively add jobs to data. Runs various checks
    """
    for job_id in uuid_list:
        # print(f"INFO: Running: {job_id}")
        job_data = old_data['links'][job_id]
        if migrate_old_job(job_data):
            # Add job to data
            # print(f"\tDEBUG: Added: {job_id}")
            data['links'][job_id] = job_data
        else:
            # Job not added
            # print(f"\tDEBUG: IGNORED: {job_id}")
            # print(f"DEBUG: IGNORED:\n {job_id}: {json.dumps(job_data, indent=2)}")
            suggestions = []
            for l in job_data.get('exit_codes'):
                link_id = job_data['exit_codes'][l].get('link_id')
                if link_id:
                    print(f"INFO: {link_id}")
                    suggestions.append(link_id)
                
            # suggestions = [job_data['exit_codes'][l].get('link_id') for l in job_data.get('exit_codes') if job_data['exit_codes'][l].get('link_id') != None]
            if job_data.get('fallback_link_id') not in suggestions:
                suggestions.append(job_data['fallback_link_id'])
            if suggestions:
                print("========== Adding Suggestions ==========")
                migrate_and_add_jobs(suggestions, data, old_data)
                print("========== End Suggestions ==========")
                
    dead_links = check_dict_dead_links(data)
    if dead_links:
        # print(f"Dead Links: {len(dead_links)}")
        print(f"Dead Links: {dead_links}")
    
if __name__ == "__main__":
    
    print("========== Current ==========")
    with open('/home/cameron/penwern/a3m_penwern/a3m/assets/workflow.json', 'r') as file:
        data = json.load(file)
    
    print("========== Old ==========")
    with open('/home/cameron/penwern/a3m_penwern/a3m/assets/workflow_old.json', 'r') as file:
        old_data = json.load(file)

    print("========== DIP ==========")
    # Populate DIP Jobs
    old_dip_jobs = []
    for job, attributes in old_data['links'].items():
        old_dip_jobs.extend(gather_dip_jobs_uuids(attributes, job))
    
    unique_dip_job_uuids = list(set(old_dip_jobs))
    print(f"Old DIP Jobs: {len(unique_dip_job_uuids)}")
    
    # Migrate DIP jobs to new version and add to new_data
    migrate_and_add_jobs(unique_dip_job_uuids, data, old_data)
            

    # print("========== Recursive ==========")
    # count = 0
    # while count < 1:
    #     count += 1
    #     print(f"========== Take {count} ==========")
    #     dead_links = check_dict_dead_links(data)
    #     migrate_and_add_jobs(dead_links, data, old_data)
        
    with open('/home/cameron/penwern/a3m_penwern/a3m/assets/workflow_test.json', 'w') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    
    validate_json(data)
    
