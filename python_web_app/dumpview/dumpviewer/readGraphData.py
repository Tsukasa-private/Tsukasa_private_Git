import pymysql
import pymysql.cursors
import json
import pandas as pd
import numpy as np
from dumpconf import connection
import datetime
epoch = datetime.datetime.utcfromtimestamp(0)
import pandas

mostRecentDataUpdate = False
mostRecentGraphData = False

sqlQuery_p_m_d_h ="""SELECT prediction_model_id, prediction_model_revision, in_or_out, descriptor_id
                            FROM prediction_model_descriptor_history"""
sqlQuery_p_m_h   ="""SELECT prediction_model_id,prediction_model_revision,
                            modified_time, deleted, creator_id, description FROM prediction_model_history"""
sqlQuery_p_m_n_h ="""SELECT prediction_model_id, prediction_model_revision, name FROM prediction_model_name_history where preferred = 1"""
sqlQuery_d_h     ="""SELECT descriptor_id, descriptor_revision, modified_time, deleted FROM descriptor_history"""
sqlQuery_d_n_h   ="""SELECT descriptor_id, descriptor_revision, name FROM descriptor_name_history where preferred = 1"""
sqlQuery_f       ="""SELECT folder_id, folder_name, parent_folder_id, creation_time, modified_time, deleted from folder"""
sqlQuery_f_p     ="""SELECT folder_id, prediction_model_id from folder_prediction_model"""


def newerGraphDataAvailable(mostRecentDataUpdate, connection):
    result = False
    query = 'SELECT TABLE_NAME, UPDATE_TIME FROM information_schema.tables WHERE TABLE_SCHEMA = "{0}" AND UPDATE_TIME IS NOT NULL'.format(connection.connection()[3])
    mostRecentTableUpdateTimes = getQueryData(query, connection)

    if not mostRecentDataUpdate:
        result = True
    elif mostRecentTableUpdateTimes:
        for item in mostRecentTableUpdateTimes:
            if item["UPDATE_TIME"] > mostRecentDataUpdate:
                result = True
    return result

def getQueryData(query, connection):
    connectiondb = connection.connection()
    conn = pymysql.connect(
      host=connectiondb[0], user=connectiondb[1], password=connectiondb[2], db=connectiondb[3], charset='utf8', cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    cursor.execute(query)
    data = cursor.fetchall()
    return data

def getQueryDataPandas(connection):
    connectiondb = connection.connection()
    conn = pymysql.connect(
      host=connectiondb[0], user=connectiondb[1], password=connectiondb[2], db=connectiondb[3], charset='utf8', cursorclass=pymysql.cursors.DictCursor
    )
    df_p_m_d_h =pd.read_sql(sqlQuery_p_m_d_h, conn)
    df_p_m_h   =pd.read_sql(sqlQuery_p_m_h, conn)
    df_p_m_n_h =pd.read_sql(sqlQuery_p_m_n_h, conn)
    df_d_h     =pd.read_sql(sqlQuery_d_h, conn)
    df_d_n_h   =pd.read_sql(sqlQuery_d_n_h, conn)
    df_f       =pd.read_sql(sqlQuery_f, conn)
    df_f_p     =pd.read_sql(sqlQuery_f_p, conn)

    #記述子情報取得
    df_descriptor = pd.merge(df_d_h, df_d_n_h, how ='left', on =['descriptor_id','descriptor_revision'])
    df_descriptor['D_name'] = df_descriptor[['name','descriptor_id']].apply(lambda x: '{} (id : {})'.format(x[0],x[1]), axis=1)

    #予測モデル情報取得
    df_prediction_model_temp = df_p_m_h[['prediction_model_id','prediction_model_revision','modified_time','deleted']]
    df_prediction_model = pd.merge(df_prediction_model_temp, df_p_m_n_h, how = 'left', on =['prediction_model_id','prediction_model_revision'])
    df_prediction_model['P_name'] = df_prediction_model[['name','prediction_model_id']].apply(lambda x: '{} (id : {})'.format(x[0],x[1]), axis=1)

    #予測モデルと記述子の関係性情報の取得　
    df_prediction_model_temp2 = df_p_m_h[['prediction_model_id','prediction_model_revision','creator_id','description','modified_time','deleted']]
    df_relation_temp= pd.merge(df_p_m_d_h, df_prediction_model_temp2, how ='left', on =['prediction_model_id','prediction_model_revision'])
    df_relation2 = pd.merge(df_relation_temp, df_prediction_model, how='left', on = ['prediction_model_id','prediction_model_revision','modified_time','deleted'])
    df_relation2 = df_relation2[["prediction_model_id","P_name","prediction_model_revision","in_or_out"
                 ,"descriptor_id","creator_id","description","modified_time","deleted"]]
    df_relation = pd.merge(df_relation2, df_descriptor, how='left', on = 'descriptor_id')
    df_relation = df_relation.rename(columns = {'modified_time_x':'P_modified_time','modified_time_y':'D_modified_time'
                                  ,'deleted_x':'P_deleted','deleted_y':'D_deleted'
                                  ,'prediction_model_revision':'P_revision','descriptor_revision':'D_revision'})

    #辞書情報取得
    folder = df_f
    folder = folder.replace(np.nan, '',regex = True)

    count_i = folder.groupby('folder_name')['folder_id'].nunique().reset_index()
    parent_folder = folder[folder.parent_folder_id == '']

    count_p = parent_folder.groupby('folder_name')
    print('辞書数: ',len(count_p))

    folder_i = folder.copy()
    parent_folder_i = parent_folder.copy()

    i = 0
    #辞書再現
    while len(count_i) > len(count_p) :

        folder_j = pd.merge(folder_i,parent_folder_i, how='left', left_on ="parent_folder_id", right_on = "folder_id")
        folder_j = folder_j.rename(columns={'folder_id_x':'folder_id','folder_name_x':'folder_name'
                                      ,'parent_folder_id_x':'parent_folder_id','deleted_x':'deleted','folder_name_y':'folder_name_P'
                                      ,'creation_time_x':'creation_time','modified_time_x':'modified_time'})
        folder_j = folder_j[["folder_id","folder_name","parent_folder_id","deleted","folder_name_P","creation_time","modified_time"]]
        folder_j = folder_j.replace(np.nan, '',regex = True)

        def FolderNameChange(row):

            if row["folder_name_P"] == '':
                return row["folder_name"]
            else:
                return row["folder_name_P"]

        folder_j['folder_name'] = folder_j.apply(FolderNameChange, axis=1)


        def P_FolderIdChange(row):
            if row["folder_name_P"] != '':
                parent_folder_id = ''
            else:
                return row["parent_folder_id"]

        folder_j['parent_folder_id'] = folder_j.apply(P_FolderIdChange, axis=1)

        folder_j = folder_j.replace(np.nan, '',regex = True)
        folder_j = folder_j[["folder_id","folder_name","parent_folder_id","deleted","creation_time","modified_time"]]

        count_i = folder_j.groupby('folder_name')['folder_id'].nunique().reset_index()
        print(i,'回目:',len(count_i))

        parent_folder_i = folder_j[folder_j.parent_folder_id == '']
        folder_i = folder_j
        i += 1

    folder_complete = pd.merge(folder_j, df_f_p, how = 'left', on = 'folder_id')
    folder_complete = folder_complete[["folder_id", "folder_name", "deleted", "prediction_model_id","creation_time","modified_time"]]
    folder_complete = folder_complete.rename(columns = {'deleted':'Dic_deleted','creation_time':'Dic_creation_time','modified_time':'Dic_modified_time'})
    data_complete = pd.merge(df_relation, folder_complete, how = "left", on = "prediction_model_id")
    data_complete = data_complete.rename(columns={'description':'P_description','folder_name':'Dic_name','creator_id':'C_id'})
    data_complete = data_complete.replace(np.nan, "", regex = True)
    data_complete_dict = data_complete.to_dict('records')

    return data_complete_dict

def getGraphData():
    global mostRecentDataUpdate
    global mostRecentGraphData
    if (newerGraphDataAvailable(mostRecentDataUpdate, connection)):
        mostRecentDataUpdate = datetime.datetime.now()
        mostRecentGraphData = getQueryDataPandas(connection)
    return mostRecentGraphData

def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0

def extractGraphData(data):
    creatorIds = []
    dicNames = []
    creatorIDToDicNames = {}

    selectRestrictData = []
    pred_desc_id_map = {}
    dic_id_map = {"mock": {}}

    for row in data:

        if not row["folder_id"] in dic_id_map["mock"]:
            dic_id_map["mock"][row["folder_id"]] = []
        if not row["prediction_model_id"] in pred_desc_id_map:
            pred_desc_id_map[row["prediction_model_id"]] = {}
        if not row["descriptor_id"] in pred_desc_id_map[row["prediction_model_id"]]:
            pred_desc_id_map[row["prediction_model_id"]][row["descriptor_id"]] = []

        selectRestrictEntry = {
            "in_or_out": row["in_or_out"],
            "prediction_model_id": row["prediction_model_id"],
            "descriptor_id": row["descriptor_id"],
            "folder_id": row["folder_id"],
            "C_id": row["C_id"],
            "Dic_modified_time": unix_time_millis(pandas.to_datetime(row["Dic_modified_time"]).to_datetime()),
            "D_name": row["D_name"],
            "P_name": row["P_name"],
            "Dic_name": row["Dic_name"],
            "P_description": row["P_description"],
            "P_modified_time": unix_time_millis(pandas.to_datetime(row["P_modified_time"]).to_datetime()),
            "P_deleted": row["P_deleted"],
            "D_modified_time": unix_time_millis(pandas.to_datetime(row["D_modified_time"]).to_datetime()),
            "D_deleted": row["D_deleted"],
            "Dic_creation_time": unix_time_millis(pandas.to_datetime(row["Dic_creation_time"]).to_datetime()),
            "Dic_deleted": row["Dic_deleted"]
        }
        selectRestrictData.append(selectRestrictEntry)
        pred_desc_id_map[row["prediction_model_id"]][row["descriptor_id"]].append(selectRestrictEntry)
        dic_id_map["mock"][row["folder_id"]].append(selectRestrictEntry)
        
        if not row["C_id"] in creatorIds:
            creatorIds.append(row["C_id"])
        if row["Dic_name"] and not row["Dic_name"] in dicNames:
            dicNames.append(row["Dic_name"])
        if row["C_id"] and row["Dic_name"]:
            if not row["C_id"] in creatorIDToDicNames:
                creatorIDToDicNames[row["C_id"]] = []
            if not row["Dic_name"] in creatorIDToDicNames[row["C_id"]]:
                creatorIDToDicNames[row["C_id"]].append(row["Dic_name"])
        
    creatorIds.sort()
    dicNames.sort()

    return {
        "selectRestrictDataJSON": json.dumps(selectRestrictData),
        "pred_desc_id_map": pred_desc_id_map,
        "dic_id_map_JSON": json.dumps(dic_id_map),
        "pred_desc_id_map_JSON": json.dumps(pred_desc_id_map),
        "creatorIds": creatorIds,
        "dicNames": dicNames,
        "creatorIDToDicNamesJSON": json.dumps(creatorIDToDicNames),
    }
