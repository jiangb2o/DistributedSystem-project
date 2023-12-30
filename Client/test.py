from queue import Queue

def inQueue(queue, value):
    '''判断元素是否在队列中'''
    tmp_queue = Queue()
    flag = False
    while not queue.empty():
        element = queue.get()
        tmp_queue.put(element)
        if element == value:
            flag = True
    while not tmp_queue.empty():
        queue.put(tmp_queue.get())

    return flag

def printq(q):
    tmp_queue = Queue()
    while not q.empty():
        element = q.get()
        print(element)
        tmp_queue.put(element)

    while not tmp_queue.empty():
        q.put(tmp_queue.get())

q = Queue()
q.put(1)
q.put(2)
q.put(3)
q.put(4)

printq(q)
print(inQueue(q, 2))
printq(q)