# -*- coding: utf-8 -*-

class Process: # Процесс (пациент)
    def __init__(self, pid, total_cpu, io_requests):
        self.pid = pid #Номер процесса 
        self.total_cpu = total_cpu
        self.io_requests = io_requests   
           # Список обращений к вводу-выводу: [(когда, длительность),
        self.cpu_used = 0  #Сколько уже отработано
        self.state = 'ready'   #Состояние: ready, running, waiting, finished
        self.next_io_index = 0  #Индекс следующего I/O запроса в списке
        self.completion_time = 0  #Момент завершения процесса

    def reset(self): 
        #Сброс в исходное состояние перед вторым запуском
        self.cpu_used = 0
        self.state = 'ready'
        self.next_io_index = 0
        self.completion_time = 0

    def has_io_request(self): #Проверить, наступило ли время делать I/O (по cpu_used)
        if self.next_io_index < len(self.io_requests):
            offset, _ = self.io_requests[self.next_io_index]
            return self.cpu_used >= offset
        return False

    def get_io_duration(self):   #Получить длительность текущего I/O
        if self.next_io_index < len(self.io_requests):
            return self.io_requests[self.next_io_index][1]
        return 0

    def advance_io(self):   #Перейти к следующему I/O запросу
        self.next_io_index += 1


class Scheduler:  #Планировщик (врач, диспетчер)
    def __init__(self, processes, quantum, blocking_mode):
        self.processes = processes  #Список всех процессов
        self.quantum = quantum  #Квант времени (максимум непрерывной работы)
        self.blocking_mode = blocking_mode   # Режим: True – с блокировкой (прерывания), 
        #False – без блокировки (busy wait)
        self.ready_queue = []
        self.waiting_queue = []   # Очередь процессов, ждущих окончания I/O (хранит
        self.current = None
        self.time = 0
        self.log = []

    def log_event(self, event, proc=None):
        pname = "P%d" % proc.pid if proc else "---"
        self.log.append((self.time, pname, event))

    def run(self):
        for p in self.processes:
            p.reset()
            self.ready_queue.append(p)

        self.current = None #Процесс, который сейчас выполняется на процессоре
        self.time = 0 #Глобальное модельное время

        while self.ready_queue or self.waiting_queue or self.current:
        
            to_wake = []
            for i, (p, rem_io, wakeup) in enumerate(self.waiting_queue):
                if wakeup <= self.time:
                    to_wake.append((p, i))
            for p, idx in reversed(to_wake):
                del self.waiting_queue[idx]
                p.state = 'ready'
                self.ready_queue.append(p)
                self.log_event("I/O complete", p)

         
            if self.current is None and self.ready_queue:
                self.current = self.ready_queue.pop(0)
                self.current.state = 'running'
                self.remaining_quantum = self.quantum
                self.log_event("Scheduled", self.current)

           
            if self.current is None:
                if self.waiting_queue:
                    next_wake = min(w for _, _, w in self.waiting_queue)
                    self.time = next_wake
                    continue
                else:
                    break

           
            remaining_cpu = self.current.total_cpu - self.current.cpu_used
            quantum_left = self.remaining_quantum
            step = min(quantum_left, remaining_cpu)

            if self.current.has_io_request():
                step = 0  

            if step > 0:
              
                self.time += step
                self.current.cpu_used += step
                self.remaining_quantum -= step
            
                if self.current.cpu_used >= self.current.total_cpu:
                    self.current.state = 'finished'
                    self.current.completion_time = self.time
                    self.log_event("Finished", self.current)
                    self.current = None
                    continue

            
            if self.current and self.current.has_io_request():
                io_dur = self.current.get_io_duration()
                self.log_event("I/O request (duration %d)" % io_dur, self.current)
                if self.blocking_mode:
                    # block process
                    self.current.state = 'waiting'
                    self.waiting_queue.append((self.current, io_dur, self.time + io_dur))
                    self.current.advance_io()
                    self.current = None
                else:
                    
                    self.log_event("Busy wait I/O (no block)", self.current)
                    self.time += io_dur
                    self.current.advance_io()
                continue

            if self.remaining_quantum <= 0 and self.current:
                self.current.state = 'ready'
                self.ready_queue.append(self.current)
                self.log_event("Quantum expired", self.current)
                self.current = None

        return self.time

    def print_log(self):
        print("\n%-6s %-8s %s" % ("Time", "Proc", "Event"))
        for t, p, e in self.log:
            print("%-6d %-8s %s" % (t, p, e))

    def print_stats(self, title):
        print("\n" + "="*60)
        print(title)
        print("Total simulation time: %d" % self.time)
        for p in self.processes:
            print("  P%d finished at %d (CPU needed %d)" % (p.pid, p.completion_time, p.total_cpu))
        print("="*60)


def main():
    # Создаёт три процесса с заданными параметрами
    processes = [
        Process(1, 10, [(5, 3)]),
        Process(2, 8,  [(2, 2), (6, 1)]),
        Process(3, 12, [(4, 4)]),
    ]
    quantum = 4

    print("=== LAB 5: INTERRUPT HANDLING ===")
    print("Quantum = %d" % quantum)
    for p in processes:
        print("P%d: CPU=%d, I/O=%s" % (p.pid, p.total_cpu, p.io_requests))

    sched1 = Scheduler(processes, quantum, blocking_mode=False)
    time1 = sched1.run()
    sched1.print_log()
    sched1.print_stats("MODE 1: WITHOUT BLOCKING (busy wait)")

   
    sched2 = Scheduler(processes, quantum, blocking_mode=True)
    time2 = sched2.run()
    sched2.print_log()
    sched2.print_stats("MODE 2: WITH BLOCKING (interrupts)")

    print("\nCOMPARISON:")
    print("  No blocking time: %d" % time1)
    print("  With blocking time: %d" % time2)
    if time1 < time2:
        print("  No blocking is faster by %d" % (time2 - time1))
    elif time2 < time1:
        print("  With blocking (interrupts) is faster by %d" % (time1 - time2))
    else:
        print("  Both equal")
    print("="*60)


if __name__ == "__main__":
    main()