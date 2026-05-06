from flask import jsonify


def success_response(data=None, message='success', code=200):
    return jsonify({'code': code, 'message': message, 'data': data}), code


def error_response(message, code=400, **extra):
    payload = {'code': code, 'message': message}
    payload.update(extra)
    return jsonify(payload), code
