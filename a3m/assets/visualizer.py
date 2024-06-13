import json
from graphviz import Digraph

# Load workflow from JSON
with open('workflow.json', 'r') as f:
    workflow = json.load(f)

# Initialize directed graph
graph = Digraph()

# Add nodes (tasks) to the graph
for task_id, task_data in workflow['links'].items():
    description = task_data.get('description', {}).get('en', task_id)
    graph.node(task_id, label=f"{description}\n({task_id})")

# Add edges (links) to the graph
for task_id, task_data in workflow['links'].items():
    if task_data['config']['@manager'] == 'linkTaskManagerChoice':
        if 'choices' in task_data['config']:
            choices = task_data['config']['choices']
            for choice in choices:
                next_task_id = choice['link_id']
                value = choice['value']
                label = str(value)
                graph.edge(task_id, next_task_id, label=label)
        elif 'chain_choices' in task_data['config']:
            chain_choices = task_data['config']['chain_choices']
            for next_task_id in chain_choices:
                graph.edge(task_id, next_task_id, label="Chain Choice")
    else:
        for exit_code, exit_data in task_data.get('exit_codes', {}).items():
            next_task_id = exit_data.get('link_id') 
            if next_task_id:
                graph.edge(task_id, next_task_id, label=str(exit_code))
        fallback_link_id = task_data.get('fallback_link_id') 
        if fallback_link_id:
            graph.edge(task_id, fallback_link_id, color='red')

# Render and display the graph
graph.render('workflow_graph', format='png', cleanup=True)
