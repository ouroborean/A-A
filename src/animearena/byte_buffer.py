


class ByteBuffer():

    buff: list[bytes]
    read_pos: int
    buff_updated: bool

    def __init__(self):
        self.buff = [] 
        self.read_pos = 0
        self.buff_updated = False

    def get_read_pos(self) -> int:
        return self.read_pos

    def get_byte_array(self) -> bytearray:
        return bytearray(self.buff)
    
    def count(self) -> int:
        return len(self.buff)
    
    def length(self) -> int:
        return self.count() - self.read_pos
    
    def clear(self):
        self.buff.clear()
    
    def write_byte(self, input: bytes):
        self.buff.extend(input)
        self.buff_updated = True

    def write_bytes(self, input: list[bytes]):
        self.buff.extend(input)
        self.buff_updated = True

    def write_int(self, input: int):
        self.buff.extend(input.to_bytes(4, 'big', signed=True))
        self.buff_updated = True
    
    def write_string(self, input: str):
        self.buff.extend(len(input).to_bytes(4, 'big'))
        self.buff.extend(input.encode('utf-8'))
        self.buff_updated = True
    
    def read_bytes(self, length: int, peek: bool = True) -> list[bytes]:
        if self.count() > self.read_pos:
            if self.buff_updated:
                self.buff_updated = False
            output = self.buff[self.read_pos:self.read_pos + length]
            if peek:
                self.read_pos += length
            return output

    def read_int(self, peek: bool = True) -> int:
        if self.count() > self.read_pos:
            if self.buff_updated:
                self.buff_updated = False
            output = int.from_bytes(self.buff[self.read_pos:self.read_pos+4], 'big', signed=True)
            if peek and self.count() > self.read_pos:
                self.read_pos += 4
            return output
    
    def read_string(self, peek: bool = True) -> str:
        length = self.read_int(True)
        if self.buff_updated:
            self.buff_updated = False
        output = ""
        output = output.join([x.to_bytes(1, 'big').decode('utf-8') for x in self.buff[self.read_pos:self.read_pos + length]])
        if peek and self.count() > self.read_pos:
            if len(output) > 0:
                self.read_pos += length
        return output
