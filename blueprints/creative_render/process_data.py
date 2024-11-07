from typing import List,Dict,Any

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

def parse_text_lines(lines_dict):
    lines = []
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

def segragate_images_and_text(data:Dict[str,Any]):
    try:
        data= dict(eval(data))
        name=data.get("name",None)
        category=data.get("category_name",None)
        images = []
        texts = []
        # Separate images and texts dynamically
        for key, value in data.items():
            if key.startswith("img"):
                img_num = int(key[3])  # Extract the image number
                while len(images) < img_num:
                    images.append({})
                images[img_num - 1][key[5:]] = value  # Add property to correct image dict
                images[img_num - 1]["number"] = img_num
            elif key.startswith("text"):
                text_num = int(key[4])  # Extract the text number
                while len(texts) < text_num:
                    texts.append({})
                if key.endswith("lines"):
                    texts[text_num - 1]["lines"] = parse_text_lines(value)
                else:
                    texts[text_num - 1][key[6:]] = value
                texts[text_num - 1]["number"] = text_num
        return images, texts, name, category
    except Exception as e:
        print(f"Error: {data}")
        raise e
        

def process_models(models:List[str]):
    list_of_text_types=[]
    for index,model in enumerate(models):
        images,text_list,name,category=segragate_images_and_text(model)
        list_of_text_types.append({
            'name':name,
            'category':category,
            'images':images,
            'text_list':text_list   
        })
    return list_of_text_types

def add_db_data(db_data:Dict[str,Any],processed_data:List[Dict[str,Any]]):
    for data in processed_data:
        count=0
        for image in data['images']:
            if count>=4:
                break
            if image['number'] in [1,2,3,4]:
                image['url']=db_data.get(f'img_{image["number"]}',None)
                count+=1
    return processed_data


def get_element_list(model: Dict[str,Any]):
    element_list={}
    # string to dict
    model= dict(eval(model))
    for key,value in model.items(): 
        element_list[key]=value
    return element_list