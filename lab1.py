# -*- coding: utf-8 -*-
#Чтобы положить в стек не просто число,
#  а объект с именем и типом. Как бирка на коробке.
class Var(object):
    def __init__(self, name, value, value_type):
        self.name = name
        self.value = value
        self.type = value_type

    def __repr__(self):
        return u"{0} : {1} ({2})".format(self.name, self.value, self.type)

#Это имитация стека памяти компьютера.
#здесь Чтобы хранить временные переменные (как fd).
class Stack(object):
    def __init__(self):
        self._data = []

    def push(self, var):
        self._data.append(var)
        print(u"[СТЕК] + помещена переменная: {}".format(var))

    def pop(self):
        if not self._data:
            print(u"[СТЕК] ! предупреждение: стек пуст")
            return None
        var = self._data.pop()
        print(u"[СТЕК] - удалена переменная: {}".format(var))
        return var

    def peek(self):
        if not self._data:
            return None
        return self._data[-1]

    def display(self):
        if not self._data:
            print(u"[СТЕК] стек пуст")
        else:
            print(u"[СТЕК] содержимое (дно -> вершина):")
            for i, var in enumerate(self._data):
                print(u"  {0:2d}: {1}".format(i, var))


class Kernel(object): #ядро операционной системы
    def __init__(self):
        self._fs = {}
        self._cwd = "/"
        self._next_fd = 10
        self._fd_table = {}
        self._fs["/"] = {"type": "dir", "children": set()}

    def _resolve_path(self, path):
         # добавляет папку или файл в словарь _fs
        if path.startswith('/'):
            # Абсолютный путь
            parts = path.split('/')[1:]  # убираем первый пустой элемент
        else:
            # Относительный путь: начинаем с текущей директории
            if self._cwd == "/":
                parts = []
            else:
                parts = self._cwd.split('/')[1:]

            # Добавляем компоненты относительного пути
            for comp in path.split('/'):
                if comp == '' or comp == '.':
                    continue
                elif comp == '..':
                    if parts:
                        parts.pop()
                else:
                    parts.append(comp)

        if not parts:
            return "/"
        return "/" + "/".join(parts)

    def _add_entry(self, path, entry_type):
        if path in self._fs:
            return False
        if entry_type == "dir":
            self._fs[path] = {"type": "dir", "children": set()}
        else:
            self._fs[path] = {"type": "file"}

        # Добавляем запись в родительскую директорию
        parent = path[:path.rfind('/')]
        if parent == "":
            parent = "/"
        if parent in self._fs and self._fs[parent]["type"] == "dir":
            self._fs[parent]["children"].add(path)
        return True

    def _remove_entry(self, path):
        if path not in self._fs:
            return False
        parent = path[:path.rfind('/')]
        if parent == "":
            parent = "/"
        if parent in self._fs:
            self._fs[parent]["children"].discard(path)
        del self._fs[path]
        return True

    def sys_mkdir(self, path, mode):     # создать папку
        abs_path = self._resolve_path(path)
        print(u"[ЯДРО] mkdir('{}', {}) -> создание директории '{}'".format(path, mode, abs_path))
        if abs_path in self._fs:
            print(u"[ЯДРО]   ошибка: директория уже существует")
            return -1
        if not self._add_entry(abs_path, "dir"):
            print(u"[ЯДРО]   ошибка: невозможно создать директорию")
            return -1
        print(u"[ЯДРО]   директория успешно создана")
        return 0

    def sys_chdir(self, path):    # сменить папку
        abs_path = self._resolve_path(path)
        print(u"[ЯДРО] chdir('{}') -> смена директории на '{}'".format(path, abs_path))
        if abs_path not in self._fs or self._fs[abs_path]["type"] != "dir":
            print(u"[ЯДРО]   ошибка: директория не существует")
            return -1
        self._cwd = abs_path
        print(u"[ЯДРО]   текущая директория изменена на '{}'".format(self._cwd))
        return 0

    def sys_creat(self, path, mode):      # создать файл 
        abs_path = self._resolve_path(path)
        print(u"[ЯДРО] creat('{}', {}) -> создание файла '{}'".format(path, mode, abs_path))
        if abs_path in self._fs and self._fs[abs_path]["type"] == "file":
            self._remove_entry(abs_path)
        if not self._add_entry(abs_path, "file"):
            print(u"[ЯДРО]   ошибка: невозможно создать файл")
            return -1
        fd = self._next_fd
        self._next_fd += 1
        self._fd_table[fd] = abs_path
        print(u"[ЯДРО]   файл создан, получен дескриптор {}".format(fd))
        return fd

    def sys_close(self, fd):      # закрыть файл по номеру
        print(u"[ЯДРО] close({}) -> закрытие файлового дескриптора".format(fd))
        if fd not in self._fd_table:
            print(u"[ЯДРО]   ошибка: неверный дескриптор")
            return -1
        path = self._fd_table[fd]
        del self._fd_table[fd]
        print(u"[ЯДРО]   дескриптор {} закрыт (файл '{}')".format(fd, path))
        return 0

    def sys_unlink(self, path):       # удалить файл
        abs_path = self._resolve_path(path)
        print(u"[ЯДРО] unlink('{}') -> удаление файла '{}'".format(path, abs_path))
        if abs_path not in self._fs or self._fs[abs_path]["type"] != "file":
            print(u"[ЯДРО]   ошибка: файл не существует")
            return -1
        for fd, fpath in list(self._fd_table.items()):
            if fpath == abs_path:
                del self._fd_table[fd]
                print(u"[ЯДРО]   дескриптор {} автоматически закрыт".format(fd))
        self._remove_entry(abs_path)
        print(u"[ЯДРО]   файл удалён")
        return 0

    def sys_rmdir(self, path):        # удалить пустую папку
        abs_path = self._resolve_path(path)
        print(u"[ЯДРО] rmdir('{}') -> удаление директории '{}'".format(path, abs_path))
        if abs_path not in self._fs or self._fs[abs_path]["type"] != "dir":
            print(u"[ЯДРО]   ошибка: директория не существует")
            return -1
        children = self._fs[abs_path].get("children", set())
        if children:
            print(u"[ЯДРО]   ошибка: директория не пуста (содержит {})".format(children))
            return -1
        self._remove_entry(abs_path)
        print(u"[ЯДРО]   директория удалена")
        return 0

    def sys_getcwd(self):       # узнать текущую папку
        return self._cwd

    def call(self, syscall_name, *args):
        print(u"\n[ВЫЗОВ] системный вызов: {} с аргументами {}".format(syscall_name, args))
        if syscall_name == "mkdir":
            return self.sys_mkdir(*args)
        if syscall_name == "chdir":
            return self.sys_chdir(*args)
        if syscall_name == "creat":
            return self.sys_creat(*args)
        if syscall_name == "close":
            return self.sys_close(*args)
        if syscall_name == "unlink":
            return self.sys_unlink(*args)
        if syscall_name == "rmdir":
            return self.sys_rmdir(*args)
        print(u"[ЯДРО] неизвестный системный вызов")
        return -1


def main():
    print(u"=" * 60)
    print(u"Моделирование работы системных вызовов (Python 2.7)")
    print(u"Исходный код на C (вариант 3):")
    print(u"""
    mkdir("temp_dir", 0755);
    chdir("temp_dir");
    int fd = creat("temp_file", 0644);
    close(fd);
    unlink("temp_file");
    chdir("..");
    rmdir("temp_dir");
    """)
    print(u"=" * 60)

    stack = Stack()
    kernel = Kernel()

    kernel.call("mkdir", "temp_dir", 0o755)
    kernel.call("chdir", "temp_dir")

    fd = kernel.call("creat", "temp_file", 0o644)
    if fd >= 0:
        stack.push(Var("fd", fd, "int"))

    top_var = stack.peek()
    if top_var and top_var.name == "fd":
        kernel.call("close", top_var.value)
        stack.pop()
    else:
        print(u"[ОШИБКА] Переменная fd не найдена в стеке")

    kernel.call("unlink", "temp_file")
    kernel.call("chdir", "..")
    kernel.call("rmdir", "temp_dir")

    print(u"\n" + u"=" * 60)
    print(u"Итоговое состояние:")
    print(u"Текущая директория: {}".format(kernel.sys_getcwd()))
    stack.display()
    print(u"Открытые файловые дескрипторы: {}".format(kernel._fd_table))
    print(u"Содержимое файловой системы (существующие элементы):")
    for p in sorted(kernel._fs.keys()):
        info = kernel._fs[p]
        print(u"  {} : {}".format(p, info["type"]))
    print(u"=" * 60)


if __name__ == "__main__":
    main()