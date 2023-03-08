import pandas as pd
import glob, json
import logging
import argparse

#
LOGGING_LEVEL = "DEBUG"
myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
logging.basicConfig(format=myformat,
                    level=getattr(logging, LOGGING_LEVEL),
                    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger('')
log.info("test")

description = '''
Examples:
import from json
python import_export_json_to_xlsx.py --import_path ./ --export_xlsx=test_export.xlsx
'''
parser = argparse.ArgumentParser(
    prog='export import modbus json',
    description=description
)

parser.add_argument('--export_xlsx', default=None)  # on/off flag
parser.add_argument('--import_xlsx', default=None)  # on/off flag
parser.add_argument('--import_path', default="./")
parser.add_argument('--export_path', default="./")

args = parser.parse_args()

if args.export_xlsx is not None:
    path = f'{args.import_path}*mapping*.json'
    log.info(f'reading files from {path}')
    mapping_files = glob.glob(path)
    log.info(f'found {len(mapping_files)}')
    #
    writer = pd.ExcelWriter(args.export_xlsx, engine='xlsxwriter')
    tables = []
    master_columns_order = [
        'parameter',
        'description',
        'function',
        'max',
        'min',
        'unit',
        'defaultvalue',
        'multiplier',
        'offset',
        'map'
    ]
    #
    for mapping_file in mapping_files:
        log.info(f'processing {mapping_file}')
        table = pd.read_json(mapping_file, orient="index")
        log.info(f'{len(table)} entries found')
        columns_order = list(set(list(table.columns)) & set(master_columns_order))
        table = table[columns_order]
        sheet_name = mapping_file.split("_")[-1]
        table.to_excel(writer, sheet_name=sheet_name, startrow=1, header=True, index=True)
        tables.append(table)
        log.info(f"json written to worksheet {sheet_name} in {args.export_xlsx}")
    writer.close()

# export xlsx to files
if args.import_xlsx is not None:
    df = pd.read_excel(args.import_xlsx, None, header=1, index_col=0, engine='openpyxl');
    for json_filename, wb in df.items():
        log.info(f'creating {json_filename}')
        result = wb.to_json(orient="index")
        parsed = json.loads(result)
        json_object = json.dumps(parsed, indent=4)
        with open(json_filename, "w") as outfile:
            outfile.write(json_object)
    # xl = pd.ExcelFile(args.import_xlsx)
    # xl.sheet_names
    # l.parse(sheet_names[0])
