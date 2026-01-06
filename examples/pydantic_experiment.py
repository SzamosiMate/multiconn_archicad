from pydantic import BaseModel

class MyTestClass(BaseModel):
    key1: str
    key2: str

json_data = {
    'key1': "random data",
    'key2': "hahaha",
}

a = MyTestClass(**json_data)