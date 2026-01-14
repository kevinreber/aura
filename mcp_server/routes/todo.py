"""Todo tool routes."""

from flask import Blueprint, jsonify, request
from ..server import get_mcp_server
from ..schemas.todo import TodoInput
from ..utils.logging import get_logger
from ..utils.audit import audit_log

todo_bp = Blueprint('todo', __name__)
logger = get_logger("todo_routes")


@todo_bp.route('/tools/todo.list', methods=['POST'])
async def todo_list():
    """List todo items.
    ---
    tags:
      - Todo
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("todo.list", data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in todo.list: {e}")
        return jsonify({"error": str(e)}), 500


@todo_bp.route('/tools/todos', methods=['GET'])
async def todos_get():
    """GET endpoint for todos - frontend compatibility."""
    try:
        bucket = request.args.get('bucket')
        include_completed = request.args.get('include_completed', 'false').lower() == 'true'

        data = {'include_completed': include_completed}
        if bucket:
            data['bucket'] = bucket

        input_data = TodoInput(**data)

        from ..tools.todo import TodoTool
        todo_tool = TodoTool()
        result = await todo_tool.list_todos(input_data)

        if hasattr(result, 'dict'):
            result_dict = result.dict()
        else:
            result_dict = result

        return jsonify(result_dict)

    except Exception as e:
        logger.error(f"Error in todos GET endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@todo_bp.route('/tools/todo.create', methods=['POST'])
async def todo_create():
    """Create a new todo item.
    ---
    tags:
      - Todo
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("todo.create", data)

        # Audit log for write operation
        audit_log("todo.create", data, result, request.remote_addr)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in todo.create: {e}")
        return jsonify({"error": str(e)}), 500


@todo_bp.route('/tools/todo.update', methods=['POST'])
async def todo_update():
    """Update an existing todo item.
    ---
    tags:
      - Todo
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("todo.update", data)

        # Audit log for write operation
        audit_log("todo.update", data, result, request.remote_addr)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in todo.update: {e}")
        return jsonify({"error": str(e)}), 500


@todo_bp.route('/tools/todo.complete', methods=['POST'])
async def todo_complete():
    """Mark a todo as completed or uncompleted.
    ---
    tags:
      - Todo
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("todo.complete", data)

        # Audit log for write operation
        audit_log("todo.complete", data, result, request.remote_addr)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in todo.complete: {e}")
        return jsonify({"error": str(e)}), 500


@todo_bp.route('/tools/todo.delete', methods=['POST'])
async def todo_delete():
    """Delete a todo item.
    ---
    tags:
      - Todo
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("todo.delete", data)

        # Audit log for write operation
        audit_log("todo.delete", data, result, request.remote_addr)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in todo.delete: {e}")
        return jsonify({"error": str(e)}), 500
