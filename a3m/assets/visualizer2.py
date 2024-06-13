import json
from graphviz import Digraph

def load_workflow(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def visualize_workflow_diff(workflow1, workflow2):
    graph = Digraph()

    for task_id, task_data in workflow1['links'].items():
        description = task_data.get('description', {}).get('en', task_id)
        graph.node(task_id, label=f"{description}\n({task_id})", color='blue')

    for task_id, task_data in workflow2['links'].items():
        description = task_data.get('description', {}).get('en', task_id)
        if task_id not in workflow1['links']:
            graph.node(task_id, label=f"{description}\n({task_id})", color='red')
        else:
            if workflow1['links'][task_id] != workflow2['links'][task_id]:
                graph.node(task_id, label=f"{description}\n({task_id})", color='orange')

    for task_id, task_data in workflow1['links'].items():
        for exit_code, exit_data in task_data.get('exit_codes', {}).items():
            next_task_id = exit_data.get('link_id')
            if next_task_id:
                if next_task_id not in workflow2['links'].get(task_id, {}).get('exit_codes', {}):
                    graph.edge(task_id, next_task_id, color='red')
                else:
                    if workflow1['links'][task_id]['exit_codes'][exit_code] != workflow2['links'][task_id]['exit_codes'].get(exit_code):
                        graph.edge(task_id, next_task_id, color='orange')

    for task_id, task_data in workflow2['links'].items():
        for exit_code, exit_data in task_data.get('exit_codes', {}).items():
            next_task_id = exit_data.get('link_id')
            if next_task_id:
                if next_task_id not in workflow1['links'].get(task_id, {}).get('exit_codes', {}):
                    graph.edge(task_id, next_task_id, color='red')

    # Handle choice elements
    for task_id, task_data in workflow1['links'].items():
        if task_data['config'].get('@manager') == 'linkTaskManagerChoice':
            choices1 = task_data['config'].get('choices', [])
            choices2 = workflow2['links'].get(task_id, {}).get('config', {}).get('choices', [])
            for choice1, choice2 in zip(choices1, choices2):
                if choice1 != choice2:
                    next_task_id1 = choice1['link_id']
                    next_task_id2 = choice2['link_id']
                    value1 = choice1['value']
                    value2 = choice2['value']
                    if value1 != value2:
                        label = f"Choice: {value1} -> {value2}"
                        graph.edge(task_id, next_task_id1, label=label, color='orange')

    graph.render('workflow_diff', format='png', cleanup=True)

# Load workflow JSON files
workflow1 = load_workflow('workflow.json')
workflow2 = load_workflow('workflow_old.json')

# Visualize differences
visualize_workflow_diff(workflow1, workflow2)
