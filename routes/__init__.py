from flask import Blueprint,jsonify
from .lifestyle_shots import lifestyle_shots
api_v1 = Blueprint('api_v1', __name__)

@api_v1.route('/lifestyle_shots', methods=['GET'])
def lifestyle():
    task_ids = lifestyle_shots()
    return jsonify({"task_ids":task_ids})

# @api_v1.route('/task-status/<task_id>', methods=['GET'])
# def task_status(task_id):
#     task_result = celery.AsyncResult(task_id)
#     if task_result.status == 'PENDING' and task_result.backend.get(task_id) is None:
#         response = {
#             'task_id': task_id,
#             'status': 'NOT_FOUND',
#             'message': 'The task with the specified ID does not exist.'
#         }
#         return jsonify(response), 404

#     if task_result.state == 'PENDING':
#         response = {
#             'task_id': task_id,
#             'status': 'PENDING',
#             'message': 'The task is yet to start.'
#         }
#     elif task_result.state == 'STARTED':
#         response = {
#             'task_id': task_id,
#             'status': 'STARTED',
#             'message': 'The task is currently in progress.'
#         }
#     elif task_result.state == 'SUCCESS':
#         response = {
#             'task_id': task_id,
#             'status': 'SUCCESS',
#             'result': task_result.result
#         }
#     elif task_result.state == 'FAILURE':
#         response = {
#             'task_id': task_id,
#             'status': 'FAILURE',
#             'error': str(task_result.result),  # Include the error message
#         }
#     else:
#         response = {
#             'task_id': task_id,
#             'status': task_result.state,
#             'message': 'Unknown state'
#         }

#     return jsonify(response), 200
