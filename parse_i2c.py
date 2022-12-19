import sys
import os
import glob
import argparse
import logging
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

SMT_PATH = ""
CONFIG_FILE_NAME = "config.cfg"
LOG_FILE_NAME = "i2c_parse.log"
I2C_PREFIX = "\"I2C [2]\","
I2C_PHASE_START = "\"start\""
I2C_PHASE_ADDRESS = "\"address\""
I2C_PHASE_DATA = "\"data\""
I2C_PHASE_STOP = "\"stop\""

TRANSACTION_READ = 1
TRANSACTION_WRITE = 2
TRANSACTION_READ_FROM = 3
TRANSACTION_UNKNOWN = 4

INIT_MODE = 0
START_MODE = 1
ADDRESS_MODE = 2
DATA_MODE = 3
STOP_MODE = 4

CRLF = "\n\r"

OK = 0
FAILURE = 1

transaction_read_count = 0
transaction_write_count = 0
transaction_read_from_count = 0
transaction_unknown = 0
transactions = 0

stats_read = {}
stats_read_from = {}
stats_write = {}

def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("-i",
                        "--input",
                        nargs="+",
                        help="Select the input file")
    parser.add_argument("-c",
                        "--clean",
                        help="Clean")
    args = parser.parse_args()

    return args


def config_update(key, value):
    try:
        with open(CONFIG_FILE_NAME, "r") as config_file:
            logging.info("config_file opened for read")
            r = config_file.read()
            config = json.loads(r)
            logging.info(r)
    except:
        logging.info("config_file created")
        config = {}

    config.update({key: value})
    logging.info("config_update:")
    logging.info(config)

    # save the config file
    with open(CONFIG_FILE_NAME, "w") as config_file:
        logging.info("config_file opened for write")
        json.dump(config, config_file)


def config_read(key):
    try:
        with open(CONFIG_FILE_NAME, "r") as config_file:
            logging.info("config_file opened for read")
            r = config_file.read()
            config = json.loads(r)
            logging.info(r)
    except:
        logging.info("config_file does not exist")
        return ''

    try:
        value = config[key]
    except:
        value = ''
    logging.info('config_read = \"' + value + '\"')
    return value

def transaction_analyse(transaction, lines):

    global transaction_read_count
    global transaction_write_count
    global transaction_read_from_count
    global transactions
    global transaction_unknown
    
    transactions += 1
    transaction_split = transaction.split(",")
    logging.info(transaction_split)
    logging.info(transaction_split.count("\"address\""))
    
    address_occurence_first = transaction_split.index("\"address\"")
    logging.info(address_occurence_first)
    
    transaction_address = int(transaction_split[address_occurence_first + 4], 16)
    logging.info("transaction_address = " + str(hex(transaction_address)) + " (" + str(transaction_address) + ")")
        
    if "true" == transaction_split[address_occurence_first + 5]:
        transaction_type = TRANSACTION_READ
        transaction_read_count += 1
        transaction_register = int(transaction_split[address_occurence_first + 12], 16)
        logging.info("TRANSACTION_READ: transaction_register = " + str(hex(transaction_register)) + " (" + str(transaction_register) + ")")
        statistics_update(stats_read, transaction_address, transaction_register)
    else:
        if 1 == transaction_split.count("\"address\""):
            transaction_type = TRANSACTION_WRITE
            transaction_write_count += 1
            transaction_register = int(transaction_split[address_occurence_first + 12], 16)
            logging.info("TRANSACTION_WRITE: transaction_register = " + str(hex(transaction_register)) + " (" + str(transaction_register) + ")")
            statistics_update(stats_write, transaction_address, transaction_register)
            return OK

        if 2 == transaction_split.count("\"address\""):
            transaction_type = TRANSACTION_READ_FROM
            transaction_read_from_count += 1

            transaction_register = int(transaction_split[address_occurence_first + 12], 16)
            logging.info("TRANSACTION_READ_FROM: transaction_register = " + str(hex(transaction_register)) + " (" + str(transaction_register) + ")")
            statistics_update(stats_read_from, transaction_address, transaction_register)
            '''
            if transaction_address in stats_read_from:
                logging.info("transaction_address in stats_read_from " + str(stats_read_from))
                logging.info(str(stats_read_from[transaction_address]))
                register_stats = stats_read_from[transaction_address]
                if transaction_register in register_stats:
                    logging.info("transaction_register in stats_read_from " + str(register_stats))
                    v = register_stats[transaction_register]
                    v += 1
                    register_stats.update({transaction_register: v})
                    logging.info("transaction_register updated in stats_read_from " + str(register_stats))
                else:
                    logging.info("transaction_register NOT in register_stats " + str(register_stats))
                    register_stats.update({transaction_register: 1})
                    logging.info("   updated register_stats " + str(register_stats))
                    stats_read_from.update({transaction_address: register_stats})
                    logging.info("transaction_register NOT in register_stats - updated stats_read_from " + str(stats_read_from[transaction_address]))
            else:
                stats_read_from.update({transaction_address: {transaction_register: 1}})
                logging.info("transaction_address(" + str(transaction_address) + ") NOT in stats_read_from, updated: " + str(stats_read_from))
            '''

            data_occurence_first = transaction_split.index("\"data\"")
            data_occurence_count = transaction_split.count("\"data\"")
            logging.info("data_occurence_first = " + str(data_occurence_first))
            logging.info("data_occurence_count = " + str(data_occurence_count))
            return OK
        else:
            logging.warning("\"address\" occured "+ str(transaction_split.count("\"address\"")) + " time(s) in line " + str(lines))
            transaction_type = TRANSACTION_UNKNOWN
            transaction_unknown += 1
            return FAILURE

    logging.info(transaction_split[address_occurence_first + 5])
    return OK

def statistics_update(stat, address, register):
    #logging.info("transaction_register = " + str(hex(transaction_register)))
    #logging.info("transaction_register = " + str(hex(transaction_register)) + " (" + str(transaction_register) + ")")
    if address in stat:
        logging.info("address in stat " + str(stat))
        logging.info(str(stat[address]))
        register_stats = stat[address]
        if register in register_stats:
            logging.info("register in stat " + str(register_stats))
            v = register_stats[register]
            v += 1
            register_stats.update({register: v})
            logging.info("register updated in stat " + str(register_stats))
        else:
            logging.info("register NOT in register_stats " + str(register_stats))
            register_stats.update({register: 1})
            logging.info("updated register_stats " + str(register_stats))
            stat.update({address: register_stats})
            logging.info("register NOT in register_stats - updated stat " + str(stat[address]))
    else:
        stat.update({address: {register: 1}})
        logging.info("address(" + str(address) + ") NOT in stat, updated: " + str(stat))
    
    
def main():
    lines = 0
    starts = 0
    addresses = 0
    datas = 0
    stops = 0

    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s %(message)s',
        handlers=[logging.FileHandler(LOG_FILE_NAME), logging.StreamHandler()])
    logging.info("\n\n------------------------------------ Logging started ------------------------------------")

    args = parse_arguments()
    logging.info("args=")
    logging.info(args)

    if args.input:
        logging.info("select the input file")             
        with open(args.input[0], "r") as input_file:
            logging.info("input_file opened for read")

            input_file_abs_name = os.path.abspath(args.input[0])
            logging.info("input_file_abs_name = " + input_file_abs_name)
            #config_update('input_file_abs_name', input_file_abs_name)

            #r = input_file.readline()
            #config = json.loads(r)
            #logging.info(len(r))

            output_file_abs_name = input_file_abs_name[:input_file_abs_name.find('.')] + '.out'
            logging.info("output_file_abs_name = " + output_file_abs_name)
            
            # frame format: name,type,start_time,duration,"ack","address","read","data"
            with open(output_file_abs_name, "w") as output_file:
                phase_type = 0
                line = True
                addressed = 0
                transaction = ""
                transaction_ready = 0
                while line:
                    line = input_file.readline()
                    lines = lines + 1
                    if line.startswith(I2C_PREFIX):
                        # remove the prefix
                        line_tmp = line[len(I2C_PREFIX):]
                        line_split = line_tmp.split(",")
                        # frame format now: type,start_time,duration,"ack","address","read","data"
                        #output_file.write(str(line_split))
                        if line_tmp.startswith(I2C_PHASE_START):
                            phase_type = START_MODE
                            starts = starts + 1
                            line_current = line_tmp[:line_tmp.find(CRLF)]
                            transaction += line_current
                        if line_tmp.startswith(I2C_PHASE_ADDRESS):
                            phase_type = ADDRESS_MODE
                            addresses = addresses + 1
                            addressed = 1
                            line_current = line_tmp[:line_tmp.find(CRLF)]
                            transaction += line_current
                        if line_tmp.startswith(I2C_PHASE_DATA):
                            phase_type = DATA_MODE
                            datas = datas + 1
                            line_current = line_tmp[:line_tmp.find(CRLF)]
                            transaction += line_current
                            #"data" line is not ended with ","
                            transaction += ","
                        if line_tmp.startswith(I2C_PHASE_STOP):
                            phase_type = STOP_MODE
                            stops = stops + 1
                            # we want to include CRLF
                            transaction += line_tmp
                            output_file.write(transaction)
                            transaction_ready = 1
                            addressed = 0
                            
                    if 1 == transaction_ready:
                        transaction_analyse(transaction, lines)
                        transaction = ""
                        transaction_ready = 0
                            
            
    if args.clean:
        logging.info("clean up")

    logging.info("\n")
    logging.info("lines = " + str(lines))
    logging.info("starts = " + str(starts))
    logging.info("addresses = " + str(addresses))
    logging.info("datas = " + str(datas))
    logging.info("stops = " + str(stops))
    logging.info("decoded frames= " + str(starts + addresses + datas + stops))

    logging.info("transaction_write_count = " + str(transaction_write_count))
    logging.info("transaction_read_count = " + str(transaction_read_count))
    logging.info("transaction_read_from_count = " + str(transaction_read_from_count))
    logging.info("transaction_unknown = " + str(transaction_unknown))
    logging.info("transactions = " + str(transactions))

    logging.info("\n")
    logging.info("stats_write:\n" + str(stats_write))
    logging.info("\n")
    logging.info("stats_read:\n" + str(stats_read))
    logging.info("\n")
    logging.info("stats_read_from:\n" + str(stats_read_from))
    
    logging.info("Completed successfully!")
    sys.exit(0)
    '''
    except: Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        logging.error(message)
        # logging.error("cannot open " + selected_file_merged_name)
    '''

if __name__ == "__main__":
    main()
