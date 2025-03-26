def increment_counter(event, context):
    print(event)
    instance_id = event['instance_id']
    iterator = event['iterator']
    index = iterator['index']
    step = iterator['step']
    count = iterator['count']
    index += step
    return {
        'instance_id': instance_id,
        'index': index,
        'step': step,
        'count': count,
        'continue': index < count
    }
