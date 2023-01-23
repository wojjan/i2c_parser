import sys
import os
import glob
import argparse
import logging

SMT_PATH = ""
CONFIG_FILE_NAME = "config.cfg"
LOG_FILE_NAME = "i2c_parse.log"
I2C_PREFIX = "\"I2C"
I2C_PHASE_START = "\"start\""
I2C_PHASE_ADDRESS = "\"address\""
I2C_PHASE_DATA = "\"data\""
I2C_PHASE_STOP = "\"stop\""

WATCH_ADDRESS = 0x70
WATCH_REGISTER = 0x97

TRANSACTION_READ = 1
TRANSACTION_WRITE = 2
TRANSACTION_READ_FROM = 3
transactions_unknown = 4

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
transactions_unknown = 0
transactions = 0

stats_read = {}
stats_read_from = {}
stats_write = {}
transactions_unknown_list = [] # stores timestamp of unknown transactions

suspicious_device_data_list = []

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
    global transactions_unknown
    global suspicious_device_data_list
    
    transactions += 1
    transaction_split = transaction.split(",")
    logging.info(transaction_split)
    logging.info(transaction_split.count("\"address\""))
    
    if 0 == transaction_split.count("\"address\""):
        transactions_unknown_list.append(transaction_split[1])
        transactions_unknown += 1
        return FAILURE
    address_occurence_first = transaction_split.index("\"address\"")
    logging.info(f"address_occurence_first={address_occurence_first}")
    # f"lines={lines}"
    transaction_address = int(transaction_split[address_occurence_first + 3], 16)

    logging.info("transaction_address = " + str(hex(transaction_address)) + " (" + str(transaction_address) + ")")
    try:    
        transaction_register = int(transaction_split[address_occurence_first + 11], 16)
        logging.info("TRANSACTION_READ: transaction_register = " + str(hex(transaction_register)) + " (" + str(transaction_register) + ")")
    except ValueError:
        transactions_unknown_list.append(transaction_split[address_occurence_first+1])
        transactions_unknown += 1
        return FAILURE
        
    if "true" == transaction_split[address_occurence_first + 6]:
        transaction_type = TRANSACTION_READ
        transaction_read_count += 1
        logging.info("TRANSACTION_READ")
    else:
        if 1 == transaction_split.count("\"address\""):
            transaction_type = TRANSACTION_WRITE
            transaction_write_count += 1
            transaction_register = int(transaction_split[address_occurence_first + 11], 16)
            logging.info("TRANSACTION_WRITE: transaction_register = " + str(hex(transaction_register)) + " (" + str(transaction_register) + ")")
            data_number = transaction_split.count("\"data\"")
            statistics_update(stats_write, transaction_address, transaction_register, data_number)
            return OK

        if 2 == transaction_split.count("\"address\""):
            transaction_type = TRANSACTION_READ_FROM
            transaction_read_from_count += 1

            transaction_register = int(transaction_split[address_occurence_first + 11], 16)
            logging.info("TRANSACTION_READ_FROM: transaction_register = " + str(hex(transaction_register)) + " (" + str(transaction_register) + ")")
            data_number = transaction_split.count("\"data\"") - 1
            statistics_update(stats_read_from, transaction_address, transaction_register, data_number)
                
            if WATCH_ADDRESS == transaction_address:
                if WATCH_REGISTER == transaction_register:
                    logging.info("transaction_address = 0x70 AND transaction_register = 0x97")
                    # first "data" is for register number - skip it
                    tmp = transaction_split[transaction_split.index("\"data\"")+1:]
                    logging.info("tmp =" + str(tmp))
                    d_count = tmp.count("\"data\"")
                    logging.info("d_count= " + str(d_count))
                    d_index1 = 0
                    d_index2 = 0
                    d_list = []
                    for i in range(d_count):
                        d_index2 = tmp[d_index1:].index("\"data\"")
                        logging.info("d_index2= " + str(d_index2))
                        #data = int(tmp[d_index1 + d_index2 + 4], 16)   # int version
                        data = tmp[d_index1 + d_index2 + 4]             # hex version
                        d_list.append(data)
                        logging.info("d_list=" + str(d_list))
                        d_index1 = d_index1 + d_index2 + 1
                    suspicious_device_data_list.append(d_list)
                    logging.info("d_list= " + str(d_list))

            #data_occurence_first = transaction_split.index("\"data\"")
            #data_occurence_count = transaction_split.count("\"data\"")
            #logging.info("data_occurence_first = " + str(data_occurence_first))
            #logging.info("data_occurence_count = " + str(data_occurence_count))
            return OK
        else:
            logging.warning("\"address\" occured "+ str(transaction_split.count("\"address\"")) + " time(s) in line " + str(lines))
            transaction_type = transactions_unknown
            transactions_unknown_list.append(transaction_split[address_occurence_first+1])
            transactions_unknown += 1
            return FAILURE

    logging.info(transaction_split[address_occurence_first + 5])
    return OK
    
'''
def statistics_update(stat, address, register, data_number):
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
            register_stats.update({register: 1}) # a new entry at register number level
            logging.info("updated register_stats " + str(register_stats))
            stat.update({address: register_stats})
            logging.info("register NOT in register_stats - updated stat " + str(stat[address]))
    else:
        stat.update({address: {register: 1}}) # a new entry at device number level
        logging.info("address(" + str(address) + ") NOT in stat, updated: " + str(stat))
'''    
    
def statistics_update(stat, address, register, data_number):
    #logging.info("transaction_register = " + str(hex(transaction_register)))
    #logging.info("transaction_register = " + str(hex(transaction_register)) + " (" + str(transaction_register) + ")")
    if address in stat:
        logging.info("address in stat " + str(stat))
        logging.info(str(stat[address]))
        register_stats = stat[address]
        if register in register_stats:
            logging.info("register in stat " + str(register_stats))
            ops_per_data_number = register_stats[register]
            if data_number in ops_per_data_number:
                v = ops_per_data_number[data_number]
                v = v + 1
                ops_per_data_number.update({data_number: v})
            else:
                ops_per_data_number.update({data_number: 1}) # a new entry at data_number level
            register_stats.update({register: ops_per_data_number})
            logging.info("register updated in stat " + str(register_stats))
        else:
            logging.info("register NOT in register_stats " + str(register_stats))
            register_stats.update({register: {data_number: 1}}) # a new entry at register number level
            logging.info("updated register_stats " + str(register_stats))
            
        stat.update({address: register_stats})
        logging.info("register NOT in register_stats - updated stat " + str(stat[address]))
    else:
        stat.update({address: {register: {data_number: 1}}}) # a new entry at device number level
        logging.info("address(" + str(address) + ") NOT in stat, updated: " + str(stat))
    

def transaction_verify_suspicious(transaction, lines):
    # suspicious device/register access handling
    transaction_split = transaction.split(",")
    address_occurence_first = transaction_split.index("\"address\"")
    transaction_register = int(transaction_split[address_occurence_first + 11], 16)
    transaction_address = int(transaction_split[address_occurence_first + 3], 16)

    if 0x70 == transaction_address:
        if 0x97 == transaction_register:
            logging.info("transaction_address = 0x70 AND transaction_register = 0x97")
            d_count = transaction_split.count("\"data\"")
            d_index = 0
            d_tuple = ()
            for i in range(d_count):
                d_index = transaction_split[d_index:].index("\"data\"")
                data = int(transaction_split[d_index + 4], 16)
                d_tuple = d_tuple + (data,)
            suspicious_device_data_list.append(d_tuple)
            logging.info("d_tuple= " + str(d_tuple))



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
            logging.info("calculate total lines number in " + args.input[0] + "...")
            line = True
            total_lines = 0
            while line:
                line = input_file.readline()
                total_lines = total_lines + 1
        logging.info("total lines number = " + str(total_lines))
                
        with open(args.input[0], "r") as input_file:
            logging.info("input_file opened for read")

            input_file_abs_name = os.path.abspath(args.input[0])
            logging.info("input_file_abs_name = " + input_file_abs_name)

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
                    if line.startswith(I2C_PREFIX):
                        # remove the prefix
                        line_tmp = line[len(I2C_PREFIX):]
                        #logging.info("1:" + line_tmp)
                        # and the chars until ",
                        str_tmp = "\","
                        line_tmp = line_tmp[line_tmp.find(str_tmp) + len(str_tmp):]
                        #logging.info("2:" + line_tmp)
                        
                        #split the line into components
                        line_split = line_tmp.split(",")
                        logging.info("line_split[0]= " + line_split[0])
                        logging.info("line_split[1]= " + line_split[1])
                        # frame format now: type,start_time,duration,"ack","address","read","data"
                        #output_file.write(str(line_split))
                        if line_tmp.startswith(I2C_PHASE_START):
                            phase_type = START_MODE
                            starts = starts + 1
                            line_current = line_tmp[:line_tmp.find(CRLF)]
                            transaction += line_current
                        elif line_tmp.startswith(I2C_PHASE_ADDRESS):
                            phase_type = ADDRESS_MODE
                            addresses = addresses + 1
                            addressed = 1
                            line_current = line_tmp[:line_tmp.find(CRLF)]
                            transaction += line_current
                            #"address" line can be not ended with ","
                            if not line_current.endswith(','):
                                transaction += ","
                        elif line_tmp.startswith(I2C_PHASE_DATA):
                            phase_type = DATA_MODE
                            datas = datas + 1
                            line_current = line_tmp[:line_tmp.find(CRLF)]
                            transaction += line_current
                            #"data" line can be not ended with ","
                            if not line_current.endswith(','):
                                transaction += ","
                        elif line_tmp.startswith(I2C_PHASE_STOP):
                            phase_type = STOP_MODE
                            stops = stops + 1
                            # we want to include CRLF
                            transaction += line_tmp
                            output_file.write(transaction)
                            transaction_ready = 1
                            addressed = 0
                        else:
                            logging.warning("unrecognized transaction type " + line_split[0])
                            
                    if 1 == transaction_ready:
                        transaction_analyse(transaction, lines)
                        transaction = ""
                        transaction_ready = 0
                        #transaction_verify_suspicious(transaction, lines)
                        
                    lines = lines + 1
                    logging.info("line = " + str(lines))
            
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
    logging.info("transactions_unknown = " + str(transactions_unknown))
    logging.info("transactions = " + str(transactions))

    logging.info("\n")
    logging.info("stats_write:\n")
    #logging.info({hex(a): {hex(b): c for b, c in bc.items()} for a, bc in stats_read_from.items()})    
    logging.info('{' + '\n '.join((f"{hex(a)}: {{{', '.join(f'{hex(b)}: {c}' for b, c in bc.items())}}}" for a, bc in stats_write.items())) + '}')

    logging.info("\n")
    logging.info("stats_read:\n")
    #logging.info({hex(a): {hex(b): c for b, c in bc.items()} for a, bc in stats_read_from.items()})    
    logging.info('{' + '\n '.join((f"{hex(a)}: {{{', '.join(f'{hex(b)}: {c}' for b, c in bc.items())}}}" for a, bc in stats_read.items())) + '}')
    logging.info("\n")
    logging.info("stats_read_from:\n")
    #logging.info({hex(a): {hex(b): c for b, c in bc.items()} for a, bc in stats_read_from.items()})    
    logging.info('{' + '\n '.join((f"{hex(a)}: {{{', '.join(f'{hex(b)}: {c}' for b, c in bc.items())}}}" for a, bc in stats_read_from.items())) + '}')

    # report unknown transactions
    logging.info("\n")
    logging.info("unknown transactions: " + str(transactions_unknown_list))

    # report suspicious_device_data_list
    logging.info("\n")
    logging.info("ADDRESS_" + hex(WATCH_ADDRESS) + "__REGISTER_" + hex(WATCH_REGISTER) + "read_from_list= " + str(suspicious_device_data_list))
    
    # write the statistics to the files
    stat_file_abs_name = input_file_abs_name[:input_file_abs_name.find('.')] + '_stats_write.stat'
    try:
        stat_file = open(stat_file_abs_name, "w")
        stat_file.write('{' + '\n '.join((f"{hex(a)}: {{{', '.join(f'{hex(b)}: {c}' for b, c in bc.items())}}}" for a, bc in stats_write.items())) + '}')
        stat_file.close()
    except:
        logging.error("can't open stat_file: ", stat_file_abs_name)
        sys.exit(1)


    stat_file_abs_name = input_file_abs_name[:input_file_abs_name.find('.')] + '_stats_read.stat'
    try:
        stat_file = open(stat_file_abs_name, "w")
        stat_file.write('{' + '\n '.join((f"{hex(a)}: {{{', '.join(f'{hex(b)}: {c}' for b, c in bc.items())}}}" for a, bc in stats_read.items())) + '}')
        stat_file.close()
    except:
        logging.error("can't open stat_file: ", stat_file_abs_name)
        sys.exit(1)

    
    stat_file_abs_name = input_file_abs_name[:input_file_abs_name.find('.')] + '_stats_read_from.stat'
    try:
        stat_file = open(stat_file_abs_name, "w")
        stat_file.write('{' + '\n '.join((f"{hex(a)}: {{{', '.join(f'{hex(b)}: {c}' for b, c in bc.items())}}}" for a, bc in stats_read_from.items())) + '}')
        #stat_file.write("\n" + str(stats_read_from))
        stat_file.close()
    except:
        logging.error("can't open stat_file: ", stat_file_abs_name)
        sys.exit(1)

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
