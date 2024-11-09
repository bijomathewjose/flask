from typing import List,Dict,Any,cast
from blueprints.creative_render.types import (ImageItem, LinesType, TemplateData, TextItem,
    VectorItem)

def get_a_plus_template_models(data:List[List[str]],template_number:int):
    models=[]
    template_list=data[1:]
    template_index=template_number+1
    for template in template_list:
        category=template[0].strip()
        name=template[1].strip()
        model=template[template_index]
        if model:
            model=add_category_to_str(model,category,name)
        else:
            continue
        models.append(model)
    return models

def add_category_to_str(original_string:str,category_name:str,name:str):
    position = original_string.find('{')
    if position != -1:
        new_string = original_string[:position + 1] + f'"category_name": "{category_name}","name": "{name}",' + original_string[position + 1:]
    else:
        new_string = original_string
    return new_string

def parse_text_lines(lines_dict)->LinesType:
    lines:list[Any] = []
    for line_key, line_value in lines_dict.items():
        if line_key.startswith("line"):
            line_num = int(line_key[4])
            while len(lines) < line_num:
                lines.append({})
            lines[line_num - 1][line_key[6:]] = line_value
            lines[line_num - 1]['number'] = line_num
        else:
            # Handle metadata like "no_of_lines"
            lines_dict[line_key] = line_value
    return {"data": lines, "no_of_lines": lines_dict.get("no_of_lines", None)}
import json
def segragate(raw_data:str)->TemplateData:
    data=raw_data
    try:
        eval_data=eval(data)
        data:dict= dict(eval_data)
        images:list[Any] = []
        texts:list[Any] = []
        vectors:list[Any] = []
        # Separate images and texts dynamically
        for key in list(data.keys()):
            value=data[key]
            if key.startswith("img"):
                img_num = int(key[3])  # Extract the image number
                while len(images) < img_num:
                    images.append({})   
                images[img_num - 1][key[5:]] = value  # Add property to correct image dict
                images[img_num - 1]["number"] = img_num
                del data[key]  # Remove the processed key
            elif key.startswith("text"):
                text_num = int(key[4])  # Extract the text number
                while len(texts) < text_num:
                    texts.append({})
                if key.endswith("lines"):
                    texts[text_num - 1]["lines"] = parse_text_lines(value)
                else:
                    texts[text_num - 1][key[6:]] = value
                texts[text_num - 1]["number"] = text_num
                del data[key] 
            elif key.startswith('vector'):
                vector_num = int(key[6])
                while len(vectors) < vector_num:
                    vectors.append({})
                vectors[vector_num - 1][key[8:]] = value
                vectors[vector_num - 1]["number"] = vector_num
                del data[key]
        images=cast(List[ImageItem],images)
        texts=cast(List[TextItem],texts)
        vectors=cast(List[VectorItem],vectors)
        out:TemplateData=cast(TemplateData,{ "images":images, "text_list":texts,"vectors":vectors}|data)
        return out
    except Exception as e:
        print(f"Error: {data}")
        raise e
    
def process_models(models:List[str]) -> List[TemplateData]:
    list_of_text_types:List[TemplateData]=[]
    for i,model in enumerate(models):
        print(f"Processing model {i}")
        list_of_text_types.append(segragate(model))
    return list_of_text_types

def add_db_data(db_data:Dict[str,Any],processed_data:List[TemplateData]):
    for data in processed_data:
        count=0
        for image in data['images']:
            if count>=4:
                break
            if image['number'] in [1,2,3,4]:
                image['url']=db_data.get(f'img_{image["number"]}',None)
                count+=1
    return processed_data
