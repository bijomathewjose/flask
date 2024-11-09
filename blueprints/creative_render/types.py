
from typing import TypedDict, List, Literal
from blueprints.upload.lifestyle_shots import lifestyle_shots
ImageTypes=Literal['wb','ls','mask']
TextItemType=Literal['para','para_title','info_title','bull_title','bull','Info']
Category = Literal["A+", "food_&_groceries", "home_decor", "cosmetics", "fashion", "demo"]
Masked_Images=Literal['img_1','img_2','img_3','img_4']
Lifestyle_Shots=Literal['img_5','img_6','img_7','img_8']
class LineData(TypedDict, total=False):
    align: str
    char: str
    font: str
    font_color: str
    font_size: str
    number: int
    text_value: str

class LinesType(TypedDict, total=False):
    data: List[LineData]
    no_of_lines: str

class TextItem(TypedDict, total=False):
    angle: str
    layer: str
    lines: LinesType
    number: int
    type: TextItemType
    width: str
    x: str
    y: str


class ImageItem(TypedDict, total=False):
    angle: str
    height: str
    layer: str
    number: int
    type: ImageTypes
    url: str
    width: str
    x: str
    y: str

class VectorItem(TypedDict, total=False):
    color: str
    height: str
    layer: str
    number: int
    width: str
    x: str
    y: str

class TemplateData(TypedDict, total=False):
    background: str
    name: str
    product_count: int
    category: Category
    images: List[ImageItem]
    text_list: List[TextItem]
    vectors: List[VectorItem]

class AllProductType(TypedDict, total=False):
    banner_color: str
    bg_cat: str
    brand: str
    cat_1: str
    cat_2: str
    description: str
    id: int
    img_1: str
    img_2: str
    img_3: str
    img_4: str
    img_5: str
    img_6: str
    img_7: str
    img_8: str
    logo: str
    name: str
    price: str
    sku: str
    tags: str
    temp_number: str
    text_dump: str
