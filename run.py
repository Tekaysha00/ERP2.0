from app import create_app
from flask import Flask

import time
from flask import g, request



app = Flask(__name__)

@app.before_request
def before_request():
    g.start_time = time.time()


@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time

        print(
            f"""
================ API PERFORMANCE ================
PATH       : {request.path}
METHOD     : {request.method}
TIME       : {duration:.2f} sec
STATUS     : {response.status_code}
=================================================
"""
        )

    return response



app = create_app()



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)        