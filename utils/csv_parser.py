import pandas as pd
from app import logger

def parse_csv_to_list(csv_path):
    logger.info(f"Starting to parse CSV file: {csv_path}")
    try:
        with open(csv_path, 'r') as file:
            logger.debug(f"Successfully opened file: {csv_path}")
            data = pd.read_csv(file)
            logger.debug(f"CSV data loaded. Shape: {data.shape}")

            if 'sku_id' not in data.columns or 'process_id' not in data.columns:
                logger.error("Required columns 'sku_id' and 'process_id' not found in CSV")
                raise Exception("CSV file must contain 'sku_id' and 'process_id' columns")

            list_of_process = []
            for index, (sku_id, process_id) in enumerate(zip(data['sku_id'], data['process_id'])):
                list_of_process.append({"sku_id": sku_id, "process_id": process_id})
                if index % 10 == 0:  # Log every 10 rows processed
                    logger.debug(f"Processed {index + 1} rows")

            logger.info(f"Successfully parsed CSV. Total processes: {len(list_of_process)}")
            return list_of_process
    except Exception as e:
        logger.error(f"Error parsing CSV file: {str(e)}")
        raise