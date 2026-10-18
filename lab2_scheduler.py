# -*- coding: utf-8 -*-

import random
from collections import deque

class Thread(object):
     #Хранить данные о каждом (потоке).
    def __init__(self, process_id, thread_id, burst_time):
        self.process_id = process_id
        self.thread_id = thread_id
        self.burst_time = burst_time
        self.remaining_time = burst_time
        self.completion_time = 0
        self.waiting_time = 0

    def __repr__(self):
        return "P{}-T{}".format(self.process_id, self.thread_id)


class Process(object):
    #Сгруппировать потоки. В реальности один процесс может 
    # содержать несколько потоков. 
    def __init__(self, pid, num_threads):
        self.pid = pid
        self.threads = []
        for tid in range(1, num_threads + 1):
            burst = random.randint(3, 12)
            self.threads.append(Thread(pid, tid, burst))


def round_robin_scheduler(threads): #Карусель
    queue = deque(threads)
    current_time = 0

    while queue:
        current_thread = queue.popleft()
        current_thread.remaining_time -= 1
        current_time += 1

        if current_thread.remaining_time == 0:
            current_thread.completion_time = current_time
        else:
            queue.append(current_thread)

    for t in threads:
        t.waiting_time = t.completion_time - t.burst_time
        if t.waiting_time < 0:
            t.waiting_time = 0


def print_results(processes): # таблица
    print("=" * 70)
    print("Round Robin Scheduling (time quantum = 1)")
    print("=" * 70)
    print("{:<10} {:<10} {:<15} {:<15} {:<15}".format(
        "Process", "Thread", "Burst time", "Completion", "Waiting"))
    print("-" * 70)

    all_threads = []
    for p in processes:
        all_threads.extend(p.threads)

    all_threads.sort(key=lambda t: t.completion_time)

    for t in all_threads:
        print("{:<10} {:<10} {:<15} {:<15} {:<15}".format(
            t.process_id,
            t.thread_id,
            t.burst_time,
            t.completion_time,
            t.waiting_time
        ))
    print("=" * 70)

    avg_wait = sum(t.waiting_time for t in all_threads) / float(len(all_threads))
    print("Average waiting time: {:.2f}".format(avg_wait))
    print("=" * 70)


def main():   #организатор
    num_processes = random.randint(2, 4)
    processes = []

    for pid in range(1, num_processes + 1):
        num_threads = random.randint(1, 3)
        p = Process(pid, num_threads)
        processes.append(p)
        print("Created process P{} with {} thread(s)".format(pid, num_threads))
        for t in p.threads:
            print("  Thread T{}: burst time = {}".format(t.thread_id, t.burst_time))

    print("\nStarting Round Robin scheduling...\n")

    all_threads = []
    for p in processes:
        all_threads.extend(p.threads)

    round_robin_scheduler(all_threads)
    print_results(processes)


if __name__ == "__main__":
    main()