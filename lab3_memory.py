# -*- coding: utf-8 -*-

import random

class Frame(object):
    #Хранить страницу и её бит
    def __init__(self, page_num):
        self.page_num = page_num
        self.reference_bit = 1

class SecondChance(object):
    #Настроить контролёра.
    def __init__(self, num_frames):
        self.num_frames = num_frames
        self.frames = []
        self.pointer = 0
        self.page_faults = 0
        self.hits = 0
        self.total_requests = 0

    def reference(self, page_num):
        # обработка одного обращения к странице
#Увеличиваем счётчик запросов и выводим
        self.total_requests += 1
        print("\n[%d] Request page %d" % (self.total_requests, page_num))

        # Проверяем, есть ли страница уже в памяти (HIT)
        for i, f in enumerate(self.frames):
            if f.page_num == page_num:
                f.reference_bit = 1
                self.hits += 1
                print("    -> HIT (frame %d)" % i)
                self._print_memory()
                return

        # Если страницы нет
        self.page_faults += 1
        print("    -> PAGE FAULT")

        # Если есть свободный кадр
        if len(self.frames) < self.num_frames:
            self.frames.append(Frame(page_num))
            print("    -> New frame %d: page %d" % (len(self.frames)-1, page_num))
            self._print_memory()
            return

        # Свободных кадров нет 
        #  нужно вытеснить по алгоритму Second Chance
        while True:
            candidate = self.frames[self.pointer]
            if candidate.reference_bit == 0:
                # вытесняем эту страницу
                old_page = candidate.page_num
                self.frames[self.pointer] = Frame(page_num)
                print("    -> Evicted page %d from frame %d" % (old_page, self.pointer))
                self.pointer = (self.pointer + 1) % self.num_frames
                break
            else:
                # даём второй шанс
                candidate.reference_bit = 0
                print("    -> Page %d in frame %d got second chance (bit->0)" % (candidate.page_num, self.pointer))
                self.pointer = (self.pointer + 1) % self.num_frames

        self._print_memory()
        #Печатает все кадры в формате [страница:бит 

    def _print_memory(self):
        mem_str = []
        for i, f in enumerate(self.frames):
            mem_str.append("[%d:%d]" % (f.page_num, f.reference_bit))
        print("    Memory: " + " ".join(mem_str))

    def print_stats(self):   #статистика
        print("\n" + "="*60)
        print("STATISTICS:")
        print("  Total requests: %d" % self.total_requests)
        print("  Hits: %d" % self.hits)
        print("  Page faults: %d" % self.page_faults)
        hit_rate = 100.0 * self.hits / self.total_requests if self.total_requests else 0
        fault_rate = 100.0 * self.page_faults / self.total_requests if self.total_requests else 0
        print("  Hit rate: %.2f%%" % hit_rate)
        print("  Fault rate: %.2f%%" % fault_rate)
        print("="*60)


def main():
   
    ram_size_kb = 16
    page_size_kb = 4
    num_frames = ram_size_kb // page_size_kb   # = 4

    print("="*60)
    print("SECOND CHANCE PAGE REPLACEMENT ALGORITHM")
    print("RAM: %d KB, Page size: %d KB, Frames: %d" % (ram_size_kb, page_size_kb, num_frames))
    print("="*60)

    scheduler = SecondChance(num_frames)

    # чтобы последовательность была
    #  одинаковой при каждом запуске
    random.seed(42)   
    num_requests = random.randint(20, 30)
    requests = [random.randint(1, 10) for _ in range(num_requests)]

    print("\nReference sequence: %s\n" % requests)
    print("Starting simulation...")

    for page in requests:
        scheduler.reference(page)

    scheduler.print_stats()


if __name__ == "__main__":
    main()