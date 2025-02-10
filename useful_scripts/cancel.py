import ee

# Script utilizado para cancelar todas as tarefas pendentes no Google Earth Engine
# Inicializar a biblioteca Earth Engine
ee.Initialize()

# Listar todas as tarefas pendentes
tasks = ee.data.listOperations()

# Cancelar cada tarefa em execução ou pendente
for task in tasks:
    if 'done' not in task or not task['done']:
        ee.data.cancelOperation(task['name'])
        print(f"Tarefa {task['name']} foi cancelada.")
