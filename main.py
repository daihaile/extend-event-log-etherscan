from math import nan
from sys import intern
from pm4py.objects.conversion.log import converter as xes_converter
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.exporter.xes import exporter as xes_exporter

import json

from timeit import default_timer as timer
import api
import pandas as pd
from datetime import datetime

start = timer()
path = 'test.xes'
forsageLog = 'forsageLog.xes'
output = 'output.csv'

priceData = 'export-EtherPrice.csv'


def weiToEth(value):
    try:
        eth = float(value) / 100000000000000000
        return eth
    except ValueError:
        print(ValueError)
        print(value, type(value))
        return 0
    

def importEtherPrice(file, start = None, end = None):
    df = pd.read_csv(file)
    df['date'] = pd.to_datetime(df['UnixTimeStamp'],unit='s')
    df['Value'] = pd.to_numeric(df['Value'],errors='coerce')
    df = df.set_index(['date'])
    return df

priceDf = importEtherPrice(priceData)


def getEthPriceByDate(date):
    d = str(datetime.fromisoformat(date).strftime('%Y-%m-%d'))
    price = priceDf.loc[d]['Value']
    return price

def importLogToDF(file):
    print('Importing event log from', file)
    log = xes_importer.apply(file)
    pd = xes_converter.apply(log, variant=xes_converter.Variants.TO_DATA_FRAME)
    #print('saved to:', 'output.csv')
    #pd.to_csv('output.csv')
    return pd

# EXPORT TO EVENT LOG .xes
def export_to_XES(df):

    df.rename(columns={'concept:name': 'case:concept:name'}, inplace=True)
    parameters = {xes_converter.Variants.TO_EVENT_LOG.value.Parameters.CASE_ID_KEY: 'case:ident:piid'}
    event_log = xes_converter.apply(df, parameters=parameters, variant=xes_converter.Variants.TO_EVENT_LOG)
    xes_exporter.apply(event_log, 'test_df.xes')


def extendLog(df):
    block = None
    caseId = None
    transactions = None
    internalTransactions = None
    caseCount = 0
    iterations = 99999999
    errorCount = 0
    transactionCount = 0
    toLastCase = 0


    df.rename({'concept:name':'name', 'time:timestamp':'timestamp', "case:concept:name":"piid"}, axis='columns', inplace=True)
    df['value'] = ''
    df['receiver'] = ''
    df['txHash'] = ''
    df['sender'] = ''
    df['received'] = ''
    print('extending log')
    print(df.columns)
    for row in df.itertuples():
        if row.Index == iterations:
            break

        if row.piid != caseId:
            caseId = row.piid
            caseCount += 1
            print('')
            print(row.Index, '[CASE]', row.piid)

            if type(row.piid) != str:
                print("skip")
                continue
            print("called api")
            transactions = api.get_transactions_by_account(row.piid, internal=False)
            internalTransactions = api.get_transactions_by_account(row.piid, internal=True)
            if transactions == []:
                print('Bad API response, skipping case')
                errorCount += 1
                continue
            print('found ' + str(len(transactions)) + ' transactions') # and ' + str(len(internalTransactions)) + ' internal transactions')
        else:
            toLastCase += 1

        if block != row.blockNumber:
            block = row.blockNumber
        
        # fill row with matching data
        txHash = ""
        value = ""
        receiver = ""
        sender = ""
        received = ""
        usedTxIndex = None
        for idx, tx in enumerate(transactions):
            if tx['blockNumber'] == str(block):
                txHash = tx['hash']
                value = tx['value']
                receiver = tx['to']
                sender = tx['from']
                usedTxIndex = idx
                transactionCount += 1

        if usedTxIndex != None:
            transactions.pop(usedTxIndex)


        # prevent duplicate itx
        for idx, itx in enumerate(internalTransactions):
            if itx['blockNumber'] == str(block) and itx['to'] == row.piid:
                received = itx['value']
                itx['value'] = "0"

        # check blockNumber and transactionId if same transaction -> only 1 entry should have value
        if row.Index != 0:
            if df.at[row.Index - 1, 'transactionIndex'] == row.transactionIndex and df.at[row.Index - 1, 'blockNumber'] == row.blockNumber:
                df.at[row.Index - 1, 'value'] = None
                df.at[row.Index - 1, 'receiver'] = None
                df.at[row.Index - 1, 'txHash'] = None
                df.at[row.Index - 1, 'sender'] = None

        #dayPrice = getEthPriceByDate(str(df['timestamp'].values[row.Index]).split('T')[0])
        #todayPrice = priceDf.iloc[-1]['Value']

        #df.at[row.Index, 'dailyEtherPrice'] = dayPrice
        df.at[row.Index, 'txHash'] = txHash
        df.at[row.Index, 'value'] = value
        df.at[row.Index, 'receiver'] = receiver
        df.at[row.Index, 'sender'] = sender
        df.at[row.Index, 'received'] = received

    print('cases:', caseCount, 'transactions:', transactionCount, 'errors:', errorCount)    
    return df

def getAllTransactions(df):
    caseList = list(set(df['case:concept:name'].tolist()))
    data = []
    for idx, id in enumerate(caseList):
        transactions = api.get_transactions_by_account(id, internal=True)
        if transactions == []:
            continue
        print('[' +str(idx) + '/' + str(len(caseList)) + ']  ' +  id)
        object = {
            'id': id,
            'transactions': transactions
            }
        data.append(object)
    return data


df = importLogToDF("forsageLog_big.xes")

#print('importing log from csv')
#df = pd.read_csv('INITIAL_LOG.csv')

df = extendLog(df)
end = timer()

print('time elapsed in seconds:', end - start)
df.to_csv('extended_log.csv')




