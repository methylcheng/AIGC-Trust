import pika

def get_rabbitmq_conn_params():
    return pika.ConnectionParameters(
        host="127.0.0.1",
        port=5672,
        virtual_host="/",
        credentials=pika.PlainCredentials("guest", "guest")
    )
