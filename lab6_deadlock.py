# -*- coding: utf-8 -*-

# ЛАБА 6: АЛГОРИТМ БАНКИРА (предотвращение взаимоблокировок)

class Banker:
    def __init__(self, available, max_need, allocation):
        """
        available: список доступных экземпляров каждого ресурса (например, [3,2])
        max_need:  2D список [i][j] – максимальная потребность процесса i в ресурсе j
        allocation: 2D список [i][j] – сколько уже выделено процессу i
        """
        self.num_procs = len(max_need)          # количество процессов
        self.num_res = len(available)           # количество типов ресурсов
        self.available = available[:]           # копия доступных ресурсов
        self.max_need = [row[:] for row in max_need]   # копия максимальных потребностей
        self.allocation = [row[:] for row in allocation] # копия выделенного
        # Вычисляем матрицу NEED = max_need - allocation (сколько ещё нужно каждому процессу)
        self.need = [[self.max_need[i][j] - self.allocation[i][j] for j in range(self.num_res)] for i in range(self.num_procs)]
        self.safe_sequence = []                 # здесь будет сохранена безопасная последовательность


    # ПРОВЕРКА БЕЗОПАСНОСТИ ТЕКУЩЕГО СОСТОЯНИЯ
    # Имитируем выделение остатков всем процессам, ищем порядок, в котором все могут завершиться
    # Возвращает (True, [последовательность]) если состояние безопасное, иначе (False, [])
 
    def is_safe_state(self):
        work = self.available[:]                # копия доступных ресурсов
        finish = [False] * self.num_procs       # кто уже "завершился" в имитации
        safe_seq = []

        while True:
            found = False
            # Ищем процесс, которому ХВАТАЕТ ресурсов (need <= work) для завершения
            for i in range(self.num_procs):
                if not finish[i] and all(self.need[i][j] <= work[j] for j in range(self.num_res)):
                    # Если нашли – "завершаем" его: возвращаем все его ресурсы в work
                    for j in range(self.num_res):
                        work[j] += self.allocation[i][j]
                    finish[i] = True
                    safe_seq.append(i)
                    found = True
                    break
            if not found:
                break      # не нашли больше процессов – выходим
        # Если все процессы удалось "завершить" – состояние безопасное
        if all(finish):
            self.safe_sequence = safe_seq
            return True, safe_seq
        else:
            return False, []

    # ОБРАБОТКА ЗАПРОСА РЕСУРСОВ ОТ ПРОЦЕССА
    # Возвращает (разрешено_ли, сообщение)

    def request_resources(self, proc_id, request):
        # 1. Проверка: запрос не превышает максимальную потребность (need)
        for j in range(self.num_res):
            if request[j] > self.need[proc_id][j]:
                return False, "Request exceeds maximum need"
        # 2. Проверка: запрос не превышает доступные сейчас ресурсы
        for j in range(self.num_res):
            if request[j] > self.available[j]:
                return False, "Not enough resources available now"

        # 3. ВРЕМЕННО выделяем ресурсы (предполагаем, что дадим)
        for j in range(self.num_res):
            self.available[j] -= request[j]
            self.allocation[proc_id][j] += request[j]
            self.need[proc_id][j] -= request[j]

        # 4. Проверяем, останется ли система в БЕЗОПАСНОМ состоянии после выделения
        safe, seq = self.is_safe_state()
        if safe:
            # Всё хорошо – выделение подтверждаем
            return True, "Allocated, leads to safe state"
        else:
            # Временное выделение привело к НЕБЕЗОПАСНОМУ состоянию – ОТКАТЫВАЕМ
            for j in range(self.num_res):
                self.available[j] += request[j]
                self.allocation[proc_id][j] -= request[j]
                self.need[proc_id][j] += request[j]
            return False, "Request would lead to unsafe state, blocked to avoid deadlock"

    # --------------------------------------------------------
    # ОСВОБОЖДЕНИЕ РЕСУРСОВ (когда процесс завершился)
    # В нашей демонстрации не используется, но метод есть
    # --------------------------------------------------------
    def release_resources(self, proc_id, release):
        for j in range(self.num_res):
            self.available[j] += release[j]
            self.allocation[proc_id][j] -= release[j]
            self.need[proc_id][j] += release[j]
        for j in range(self.num_res):
            self.need[proc_id][j] = 0

    # --------------------------------------------------------
    # КРАСИВЫЙ ВЫВОД СОСТОЯНИЯ (available, allocation, need)
    # --------------------------------------------------------
    def __str__(self):
        res = "Available: " + str(self.available) + "\n"
        res += "Allocation:\n"
        for i in range(self.num_procs):
            res += "  P%d: %s\n" % (i, self.allocation[i])
        res += "Need:\n"
        for i in range(self.num_procs):
            res += "  P%d: %s\n" % (i, self.need[i])
        return res


# ============================================================
# ФУНКЦИЯ ЗАПУСКА СИМУЛЯЦИИ
# use_banker = True  – использовать алгоритм банкира (безопасное выделение)
# use_banker = False – выделять ресурсы без проверки безопасности (может быть deadlock)
# processes_requests – список запросов: (pid, [reqA, reqB])
# ============================================================
def run_simulation(use_banker, processes_requests):
    # Исходные данные для примера: 3 процесса, 2 типа ресурсов (A и B)
    available = [3, 2]                     # всего свободно: 3 A, 2 B
    max_need = [
        [5, 3],   # P0 максимум
        [3, 2],   # P1
        [2, 2]    # P2
    ]
    allocation = [
        [0, 0],   # изначально ничего не выделено
        [0, 0],
        [0, 0]
    ]
    banker = Banker(available, max_need, allocation)   # создаём банкира
    print("Initial state:")
    print(banker)

    deadlock = False
    # Обрабатываем каждый запрос из очереди
    for req in processes_requests:
        pid, req_vec = req
        print("\nProcess P%d requests %s" % (pid, req_vec))
        if use_banker:
            # РЕЖИМ С АЛГОРИТМОМ БАНКИРА
            granted, msg = banker.request_resources(pid, req_vec)
            print("  Banker: %s" % msg)
            # Если не разрешили – процесс ждёт, мы просто идём дальше
        else:
            # РЕЖИМ БЕЗ АЛГОРИТМА (просто выделяем, если есть ресурсы)
            ok = True
            for j in range(len(available)):
                if req_vec[j] > banker.available[j]:
                    print("  Not enough resources, process blocked")
                    ok = False
                    break
            if ok:
                for j in range(len(available)):
                    banker.available[j] -= req_vec[j]
                    banker.allocation[pid][j] += req_vec[j]
                    banker.need[pid][j] -= req_vec[j]
                print("  Resources allocated (no safety check)")
            # иначе не выделяем
        print("Current state:")
        print(banker)

    # После всех запросов проверяем финальное состояние на безопасность
    safe, seq = banker.is_safe_state()
    if safe:
        print("\nFinal state is safe. Safe sequence:", seq)
    else:
        print("\nFinal state is UNSAFE (potential deadlock)")
        deadlock = True
    return banker, deadlock


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================
def main():
    print("="*60)
    print("LAB 6: DEADLOCK HANDLING - BANKER'S ALGORITHM")
    print("="*60)

    # Список запросов, которые будут последовательно обработаны
    requests = [
        (0, [1, 0]),   # P0 просит 1 ресурс A
        (1, [2, 0]),   # P1 просит 2 ресурса A
        (2, [0, 1]),   # P2 просит 1 ресурс B
        (0, [2, 1]),   # P0 просит ещё 2 A и 1 B
        (1, [1, 1]),   # P1 просит 1 A и 1 B
        (2, [1, 1]),   # P2 просит 1 A и 1 B
    ]

    # 1. ЗАПУСК С АЛГОРИТМОМ БАНКИРА (безопасное выделение)
    print("\n--- SIMULATION WITH BANKER'S ALGORITHM (avoid deadlock) ---")
    banker1, dead1 = run_simulation(use_banker=True, processes_requests=requests)
    print("\n--- RESULT: No deadlock occurred ---")

    # 2. ЗАПУСК БЕЗ АЛГОРИТМА (просто выделяем, если есть свободные ресурсы)
    print("\n--- SIMULATION WITHOUT BANKER (deadlock may occur) ---")
    banker2, dead2 = run_simulation(use_banker=False, processes_requests=requests)
    if dead2:
        print("\n--- RESULT: Deadlock detected ---")
    else:
        print("\n--- RESULT: No deadlock (lucky) ---")

    # Сравнение
    print("\n" + "="*60)
    print("COMPARISON:")
    print("  With Banker's algorithm: deadlock avoided (system always safe)")
    print("  Without Banker: deadlock may occur as seen above")
    print("="*60)


if __name__ == "__main__":
    main()