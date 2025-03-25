def increment_counter(event, context):
    print(event)
    iterator = event['iterator']
    index = iterator['index']
    step = iterator['step']
    count = iterator['count']
    index += step
    return {
        'index': index,
        'step': step,
        'count': count,
        'continue': index < count
    }