from dataclasses import dataclass


@dataclass
class Par:
    name:str="Par"
    
    def __post_init__(self):
        print(f'{self.name=} post init Par')

@dataclass
class Sub(Par):
    
    def __post_init__(self):
        self.name="sub"
        super().__post_init__()
        


s=Sub()
print(s)
print(s.name)