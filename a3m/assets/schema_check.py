import json
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
    
if __name__ == "__main__":
    
    print("========== Current ==========")
    with open('/home/cameron/penwern/a3m_penwern/a3m/assets/workflow.json', 'r') as file:
        data = json.load(file)
        
    validate_json(data)
    
