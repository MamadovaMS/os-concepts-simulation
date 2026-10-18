# -*- coding: utf-8 -*-

import sys

# Склад (управление секторами)
class Disk:
    def __init__(self, num_sectors, sector_size):
        #создаёт массив секторов 
        # (data) и битовую карту свободных секторов
        self.num_sectors   = num_sectors
        self.sector_size   = sector_size
        self.data          = [''] * num_sectors   
        self.free_bitmap   = [True] * num_sectors 

    def allocate_sector(self):
        #ищет первый свободный сектор,
        #  помечает занятым, возвращает его номер.
        for i, free in enumerate(self.free_bitmap):
            if free:
                self.free_bitmap[i] = False
                self.data[i] = ''
                return i
        return -1

    def free_sector(self, sector): #освобождает сектор (помечает свободным).
        if 0 <= sector < self.num_sectors:
            self.free_bitmap[sector] = True
            self.data[sector] = ''

    def read_sector(self, sector): #читает содержимое сектора.
        if 0 <= sector < self.num_sectors:
            return self.data[sector]
        return None

    def write_sector(self, sector, content): #пишет в сектор (обрезая до размера сектора).
        if 0 <= sector < self.num_sectors:
            self.data[sector] = content[:self.sector_size]

    def get_used_sectors(self, inode_handler, inode_num):
        #собирает все номера секторов, принадлежащих файлу (прямые + косвенные).
        """Return list of sector numbers used by an inode (including indirect blocks)."""
        inode = inode_handler.get_inode(inode_num)
        if inode is None:
            return []
        sectors = list(inode.direct_blocks)  # copy
        if inode.indirect_block != -1:
            # indirect block contains list of sector numbers (as string of integers)
            ind_data = self.read_sector(inode.indirect_block)
            if ind_data:
                parts = ind_data.split(',')
                for p in parts:
                    if p.isdigit():
                        sectors.append(int(p))
        return sectors

# Карточка файла/папки
class Inode:
    def __init__(self, is_dir, size=0):
        self.is_dir = is_dir      #  тип: папка или файл.
        self.size = size           # размер содержимого (байт).
        self.direct_blocks = []    # список до 12 номеров секторов (прямые ссылки).
        self.indirect_block = -1   # номер сектора, где лежат остальные номера (если файл большой).
    def add_direct_block(self, sector):
        if len(self.direct_blocks) < 12:
            self.direct_blocks.append(sector)



class InodeHandler: #Картотека (работа с I-узлами)
    def __init__(self, disk, max_inodes=100):
        self.disk = disk
        self.inodes = {}  # inode_num -> Inode object
        self.next_inode_num = 1

    def create_inode(self, is_dir, size=0): # создаёт новый I-узел, выдаёт номер.
        ino = self.next_inode_num
        self.next_inode_num += 1
        self.inodes[ino] = Inode(is_dir, size)
        return ino

    def get_inode(self, ino): #найти I-узел по номеру.
        return self.inodes.get(ino)

    def delete_inode(self, ino):  #удалить I-узел, освободив все его сектора 
       # (и косвенный блок).
        if ino in self.inodes:
        
            inode = self.inodes[ino]
            for sector in inode.direct_blocks:
                self.disk.free_sector(sector)
            if inode.indirect_block != -1:
              
                ind_data = self.disk.read_sector(inode.indirect_block)
                if ind_data:
                    for s in ind_data.split(','):
                        if s.isdigit():
                            self.disk.free_sector(int(s))
                self.disk.free_sector(inode.indirect_block)
            del self.inodes[ino]
            return True
        return False

    def allocate_sectors_for_data(self, ino, data_bytes):
        #записать данные в файл: освободить старые сектора, 
        # выделить новые, заполнить прямые и косвенную ссылки.
        """Write data to file (overwrites previous content). Allocates new sectors."""
        inode = self.get_inode(ino)
        if inode is None:
            return False

        
        for sector in inode.direct_blocks:
            self.disk.free_sector(sector)
        if inode.indirect_block != -1:
            ind_data = self.disk.read_sector(inode.indirect_block)
            if ind_data:
                for s in ind_data.split(','):
                    if s.isdigit():
                        self.disk.free_sector(int(s))
            self.disk.free_sector(inode.indirect_block)
        inode.direct_blocks = []
        inode.indirect_block = -1

        sector_size = self.disk.sector_size
        num_sectors_needed = (len(data_bytes) + sector_size - 1) // sector_size
        allocated = []
        for _ in range(num_sectors_needed):
            s = self.disk.allocate_sector()
            if s == -1:
                
                for ss in allocated:
                    self.disk.free_sector(ss)
                return False
            allocated.append(s)
            self.disk.write_sector(s, data_bytes[_*sector_size:(_+1)*sector_size])

       
        if len(allocated) <= 12:
            inode.direct_blocks = allocated
        else:
            inode.direct_blocks = allocated[:12]
            indirect_sector = self.disk.allocate_sector()
            if indirect_sector == -1:
                
                for ss in allocated:
                    self.disk.free_sector(ss)
                return False
            inode.indirect_block = indirect_sector
           
            remaining = allocated[12:]
            self.disk.write_sector(indirect_sector, ','.join(str(s) for s in remaining))

        inode.size = len(data_bytes)
        return True

    def read_data(self, ino):  
        #прочитать файл: собрать данные из секторов 
        # по прямым и косвенным ссылкам.
        inode = self.get_inode(ino)
        if inode is None or inode.is_dir:
            return None
        content_parts = []
        for sector in inode.direct_blocks:
            content_parts.append(self.disk.read_sector(sector))
        if inode.indirect_block != -1:
            ind_data = self.disk.read_sector(inode.indirect_block)
            if ind_data:
                for s in ind_data.split(','):
                    if s.isdigit():
                        content_parts.append(self.disk.read_sector(int(s)))
        return ''.join(content_parts)

# Запись в папке
class DirEntry:
    def __init__(self, name, inode_num):
        self.name = name
        self.inode_num = inode_num

# Файловая система (главный управляющий)
class FileSystem:
    def __init__(self, num_sectors, sector_size):
        self.disk = Disk(num_sectors, sector_size)
        self.inode_handler = InodeHandler(self.disk)
        self.current_path = "/"   # absolute path
        # root directory creation
        root_inode = self.inode_handler.create_inode(is_dir=True, size=0)
        self.root_inode = root_inode
        # root directory data: list of DirEntry
        self.dir_data = {}         # inode_num -> list of DirEntry objects
        self.dir_data[root_inode] = []

    def _get_inode_from_path(self, path):
        """Return (inode_num, rest_of_path) if path exists; rest_of_path is used for deep resolve."""
        if path == '/':
            return self.root_inode, None
        if path.startswith('/'):
            path = path[1:]
        if path.endswith('/'):
            path = path[:-1]
        parts = path.split('/')
        current_ino = self.root_inode
        for i, part in enumerate(parts):
            # lookup in current directory's entries
            entries = self.dir_data.get(current_ino, [])
            found = None
            for e in entries:
                if e.name == part:
                    found = e.inode_num
                    break
            if found is None:
                return None, None
            inode = self.inode_handler.get_inode(found)
            if i == len(parts)-1:
                return found, None
            if not inode.is_dir:
                return None, None
            current_ino = found
        return None, None

    def _resolve_path(self, path):
        ino, _ = self._get_inode_from_path(path)
        return ino

    def _get_parent_inode(self, path):
        if path == '/':
            return None, None
        if path.endswith('/'):
            path = path[:-1]
        last_slash = path.rfind('/')
        if last_slash == -1:
            parent_path = '/'
            name = path
        else:
            parent_path = path[:last_slash] if last_slash > 0 else '/'
            name = path[last_slash+1:]
        parent_ino = self._resolve_path(parent_path)
        if parent_ino is None:
            return None, None
        return parent_ino, name

    def create_directory(self, name, parent_path):
        parent_ino = self._resolve_path(parent_path)
        if parent_ino is None:
            return False, "Parent directory does not exist"
        # check if already exists
        entries = self.dir_data.get(parent_ino, [])
        for e in entries:
            if e.name == name:
                return False, "Name already exists"
        # create new directory inode
        ino = self.inode_handler.create_inode(is_dir=True, size=0)
        self.dir_data[ino] = []
        # add entry to parent
        self.dir_data[parent_ino].append(DirEntry(name, ino))
        return True, "OK"

    def create_file(self, name, parent_path):
        parent_ino = self._resolve_path(parent_path)
        if parent_ino is None:
            return False, "Parent directory does not exist"
        entries = self.dir_data.get(parent_ino, [])
        for e in entries:
            if e.name == name:
                return False, "Name already exists"
        ino = self.inode_handler.create_inode(is_dir=False, size=0)
        self.dir_data[parent_ino].append(DirEntry(name, ino))
        return True, "OK"

    def delete_file(self, path):
        parent_ino, name = self._get_parent_inode(path)
        if parent_ino is None or name is None:
            return False, "Invalid path"
        entries = self.dir_data.get(parent_ino, [])
        for i, e in enumerate(entries):
            if e.name == name:
                ino = e.inode_num
                inode = self.inode_handler.get_inode(ino)
                if inode is None or inode.is_dir:
                    return False, "Not a regular file"
                # free inode and its sectors
                self.inode_handler.delete_inode(ino)
                del entries[i]
                self.dir_data[parent_ino] = entries
                return True, "OK"
        return False, "File not found"

    def delete_directory(self, path):
        parent_ino, name = self._get_parent_inode(path)
        if parent_ino is None or name is None:
            return False, "Invalid path"
        entries = self.dir_data.get(parent_ino, [])
        for i, e in enumerate(entries):
            if e.name == name:
                ino = e.inode_num
                inode = self.inode_handler.get_inode(ino)
                if inode is None or not inode.is_dir:
                    return False, "Not a directory"
                # check if empty
                sub_entries = self.dir_data.get(ino, [])
                if sub_entries:
                    return False, "Directory not empty"
                self.inode_handler.delete_inode(ino)
                del entries[i]
                self.dir_data[parent_ino] = entries
                return True, "OK"
        return False, "Directory not found"

    def write_file(self, path, content):
        ino = self._resolve_path(path)
        if ino is None:
            return False, "File not found"
        inode = self.inode_handler.get_inode(ino)
        if inode.is_dir:
            return False, "Is a directory"
        if not self.inode_handler.allocate_sectors_for_data(ino, content):
            return False, "Not enough disk space"
        return True, "OK"

    def read_file(self, path):
        ino = self._resolve_path(path)
        if ino is None:
            return None, "File not found"
        inode = self.inode_handler.get_inode(ino)
        if inode.is_dir:
            return None, "Is a directory"
        data = self.inode_handler.read_data(ino)
        return data, "OK"

    def list_dir(self, path):
        ino = self._resolve_path(path)
        if ino is None:
            return None, "Directory not found"
        inode = self.inode_handler.get_inode(ino)
        if not inode.is_dir:
            return None, "Not a directory"
        entries = self.dir_data.get(ino, [])
        result = []
        for e in entries:
            i_node = self.inode_handler.get_inode(e.inode_num)
            type_char = 'd' if i_node.is_dir else 'f'
            result.append((type_char, e.name, i_node.size, e.inode_num))
        return result, "OK"

    def tree(self, current_ino=None, prefix=''):
        if current_ino is None:
            current_ino = self.root_inode
            print('/')
            prefix = ''
        else:
            print(prefix + '└── ' + self._get_name_by_inode(current_ino))
        entries = self.dir_data.get(current_ino, [])
        for i, e in enumerate(entries):
            is_last = (i == len(entries)-1)
            new_prefix = prefix + ('    ' if is_last else '│   ')
            if self.inode_handler.get_inode(e.inode_num).is_dir:
                self.tree(e.inode_num, new_prefix)
            else:
                print(new_prefix + '└── ' + e.name)

    def _get_name_by_inode(self, ino):
        # find name of an inode from root (simplistic)
        def search(node_ino, target):
            entries = self.dir_data.get(node_ino, [])
            for e in entries:
                if e.inode_num == target:
                    return e.name
                if self.inode_handler.get_inode(e.inode_num).is_dir:
                    sub = search(e.inode_num, target)
                    if sub:
                        return sub
            return None
        return search(self.root_inode, ino) or '?'

    def get_absolute_path(self, ino, current=None):
        # not necessary for now
        return ""

    def map_disk(self, path_for_highlight):
        """Print disk sectors map: '.' free, '#' used. If path_for_highlight is given, mark its sectors as '*'."""
        highlight_sectors = set()
        if path_for_highlight:
            ino = self._resolve_path(path_for_highlight)
            if ino is not None:
                highlight_sectors = set(self.disk.get_used_sectors(self.inode_handler, ino))
        line = ''
        for i in range(self.disk.num_sectors):
            if i in highlight_sectors:
                line += '*'
            elif not self.disk.free_bitmap[i]:
                line += '#'
            else:
                line += '.'
        return line

# Интерфейс командной строки (CLI)
def main():
    print("=== File System Simulation (I-nodes) ===")
    try:
        num_sectors = int(raw_input("Enter number of sectors (e.g., 64): "))
        sector_size = int(raw_input("Enter sector size in bytes (e.g., 64): "))
    except:
        print("Invalid input, using defaults: 64 sectors, 64 bytes each.")
        num_sectors = 64
        sector_size = 64

    fs = FileSystem(num_sectors, sector_size)
    current_dir = "/"

    print("\nCommands: ls, cd, mkdir, touch, rm, rmdir, write, read, cp, mv, tree, map, pwd, quit")
    print("Example: mkdir docs; touch readme.txt; write readme.txt 'Hello world'; map readme.txt")
    print()

    while True:
        try:
            cmd_line = raw_input(current_dir + "> ").strip()
            if not cmd_line:
                continue
            parts = cmd_line.split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd == 'quit' or cmd == 'exit':
                break

            elif cmd == 'pwd':
                print(current_dir)

            elif cmd == 'ls':
                path = args[0] if args else current_dir
                listing, err = fs.list_dir(path)
                if err != "OK":
                    print("Error:", err)
                else:
                    for typ, name, size, ino in listing:
                        print("%s\t%6d\t%4d\t%s" % (typ, size, ino, name))

            elif cmd == 'cd':
                if not args:
                    pass
                elif args[0] == '/':
                    current_dir = '/'
                elif args[0] == '..':
                    if current_dir != '/':
                        parent = current_dir[:current_dir.rfind('/')]
                        current_dir = parent if parent else '/'
                else:
                    # resolve relative path
                    new_path = current_dir
                    if new_path != '/':
                        new_path += '/'
                    new_path += args[0]
                    if fs._resolve_path(new_path) is not None:
                        current_dir = new_path
                    else:
                        print("No such directory")

            elif cmd == 'mkdir':
                if not args:
                    print("Usage: mkdir <dirname>")
                    continue
                ok, msg = fs.create_directory(args[0], current_dir)
                if not ok:
                    print("Error:", msg)

            elif cmd == 'touch':
                if not args:
                    print("Usage: touch <filename>")
                    continue
                ok, msg = fs.create_file(args[0], current_dir)
                if not ok:
                    print("Error:", msg)

            elif cmd == 'rm':
                if not args:
                    print("Usage: rm <filepath>")
                    continue
                path = args[0] if args[0].startswith('/') else current_dir + '/' + args[0]
                ok, msg = fs.delete_file(path)
                if not ok:
                    print("Error:", msg)

            elif cmd == 'rmdir':
                if not args:
                    print("Usage: rmdir <dirpath>")
                    continue
                path = args[0] if args[0].startswith('/') else current_dir + '/' + args[0]
                ok, msg = fs.delete_directory(path)
                if not ok:
                    print("Error:", msg)

            elif cmd == 'write':
                if len(args) < 2:
                    print("Usage: write <filename> <content>")
                    continue
                filename = args[0]
                content = ' '.join(args[1:])
                path = filename if filename.startswith('/') else current_dir + '/' + filename
                ok, msg = fs.write_file(path, content)
                if not ok:
                    print("Error:", msg)
                else:
                    print("Written %d bytes." % len(content))

            elif cmd == 'read':
                if not args:
                    print("Usage: read <filename>")
                    continue
                filename = args[0]
                path = filename if filename.startswith('/') else current_dir + '/' + filename
                data, msg = fs.read_file(path)
                if data is None:
                    print("Error:", msg)
                else:
                    print("Content (%d bytes):\n%s" % (len(data), data))

            elif cmd == 'cp':
                # simple copy: read source, write to destination
                if len(args) != 2:
                    print("Usage: cp <src> <dst>")
                    continue
                src = args[0] if args[0].startswith('/') else current_dir + '/' + args[0]
                dst = args[1] if args[1].startswith('/') else current_dir + '/' + args[1]
                data, msg = fs.read_file(src)
                if data is None:
                    print("Error reading source:", msg)
                else:
                    ok, msg2 = fs.write_file(dst, data)
                    if not ok:
                        print("Error writing destination:", msg2)
                    else:
                        print("Copied.")

            elif cmd == 'mv':
                # rename by delete+create or move dir content (simplified)
                if len(args) != 2:
                    print("Usage: mv <src> <dst>")
                    continue
                src = args[0] if args[0].startswith('/') else current_dir + '/' + args[0]
                dst = args[1] if args[1].startswith('/') else current_dir + '/' + args[1]
                # get parent and name of destination
                parent_dst_ino, dst_name = fs._get_parent_inode(dst)
                if parent_dst_ino is None:
                    print("Invalid destination path")
                    continue
                # just rename by copying directory entry
                src_ino = fs._resolve_path(src)
                if src_ino is None:
                    print("Source not found")
                    continue
                src_inode = fs.inode_handler.get_inode(src_ino)
                # find source entry in its parent
                src_parent, src_name = fs._get_parent_inode(src)
                if src_parent is None:
                    print("Invalid source")
                    continue
                # remove source entry from its parent directory
                entries = fs.dir_data.get(src_parent, [])
                for i, e in enumerate(entries):
                    if e.name == src_name:
                        del entries[i]
                        break
                # add entry to new parent with new name
                fs.dir_data[parent_dst_ino].append(DirEntry(dst_name, src_ino))
                print("Moved/renamed.")

            elif cmd == 'tree':
                fs.tree()

            elif cmd == 'map':
                target = args[0] if args else None
                if target is None:
                    map_str = fs.map_disk(None)
                    print("Disk map ('.' free, '#' used):\n" + map_str)
                else:
                    path = target if target.startswith('/') else current_dir + '/' + target
                    map_str = fs.map_disk(path)
                    print("Disk map with highlight of '%s' ('*' = selected, '#' = other used, '.' = free):\n%s" % (target, map_str))

            else:
                print("Unknown command. Available: ls, cd, mkdir, touch, rm, rmdir, write, read, cp, mv, tree, map, pwd, quit")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()

    #Доступные команды 
    # ls [путь] – показать содержимое каталога.
    #cd <путь> – сменить текущий каталог (.. и / поддерживаются).
    #pwd – показать текущий путь.
    #mkdir <имя> – создать подкаталог в текущем каталоге.
    #touch <имя> – создать пустой файл.
    #rm <путь> – удалить файл.
    #rmdir <путь> – удалить пустой каталог.
     #write <путь> <текст> – записать текст в файл (перезаписывая). Если места не хватает – предупреждение.
    #read <путь> – прочитать содержимое файла.
    #cp <источник> <назначение> – копировать файл.
    #mv <источник> <назначение> – переместить/переименовать файл или каталог (простое переименование без перемещения между дисками).
    #tree – вывести дерево каталогов от корня.
    #map [путь] – показать карту диска: . – свободный сектор, # – занятый (и не выбранный), * – сектора, принадлежащие указанному пути (если путь задан).
    #quit – выход.