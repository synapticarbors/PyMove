from pymove import preprocessing
from pymove import utils as ut
import time
import numpy as np
import pandas as pd
from tqdm import tqdm

def union_poi_bank(df_, label_poi='type_poi'):
    print('union bank categories to one category')
    print('... There are {} -- {}'.format(df_[label_poi].nunique(), label_poi))
    filter_bank = (df_[label_poi].isin(['bancos_filiais', 'bancos_agencias', 'bancos_postos', 'bancos_PAE', 'bank']))
    df_.at[df_[filter_bank].index, label_poi] = 'banks'

def union_poi_bus_station(df_, label_poi='type_poi'):
    print('union bus station categories to one category')
    filter_bus_station = (df_[label_poi].isin(['transit_station', 'pontos_de_onibus']))
    df_.at[df_[filter_bus_station].index, label_poi] = 'bus_station'

def union_poi_bar_restaurant(df_,label_poi='type_poi'):
    print('union restaurant and bar categories to one category')
    filter_bar_restaurant = (df_[label_poi].isin(['restaurant', 'bar']))
    df_.at[df_[filter_bar_restaurant].index, label_poi] = 'bar-restaurant'

def union_poi_parks(df_, label_poi='type_poi'):
    print('union parks categories to one category')
    filter_parks = (df_[label_poi].isin(['pracas_e_parques', 'park']))
    df_.at[df_[filter_parks].index, label_poi] = 'parks'

def union_poi_police(df_, label_poi='type_poi'):
    print('union distritos policies and police categories')
    filter_police = (df_[label_poi] == 'distritos_policiais') 
    df_.at[df_[filter_police].index, label_poi] = 'police'

def join_coletives_areas(gdf_, gdf_rules_, label_geometry='geometry'):
    print('Integration between trajectories and coletives areas')
    
    polygons = gdf_rules_['geometry'].unique()
    gdf_['violation'] = False
    for p in tqdm(polygons, total=len(polygons)):
        index = gdf_[gdf_['geometry'].intersects(p)].index
        #print('attributing violations to polygon - {}'.format(i))
        gdf_.at[index, 'violation'] = True

def join_with_POIs(df_, df_POIs, label_id='name', label_POI='POI', reset_index=True):    
    try:
        print('Integration with POIs...')
        start_time = time.time()
               
        ## get a vector with windows time to each point
        if reset_index:
            print('... Reseting index to operation...')
            df_.reset_index(drop=True, inplace=True)
            df_POIs.reset_index(drop=True, inplace=True)
        
        #create numpy array to store new colum to dataframe of movement objects
        current_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
        ids_POIs= np.full(df_.shape[0], np.NAN, dtype='object_')
        tag_POIs = np.full(df_.shape[0], np.NAN, dtype='object_')
    
        # creating lat and lon array to operation
        lat_tnz = np.full(df_POIs.shape[0], np.Infinity, dtype=np.float32)
        lon_tnz = np.full(df_POIs.shape[0], np.Infinity, dtype=np.float32)
        
        for row in tqdm(df_[['lat','lon']].itertuples(), total=df_.shape[0]):
            #get lat and lon to each id
            idx = row.Index
            
            #create a vector to each lat
            lat_tnz.fill(row.lat)
            lon_tnz.fill(row.lon)

            #calculing distances to idx
            distances = np.float32(ut.distances.haversine(lat_tnz, lon_tnz, df_POIs['lat'].to_numpy(dtype=np.float32), df_POIs['lon'].to_numpy(dtype=np.float32)))
            
            # get index to arg_min and min distance
            index_min = np.argmin(distances)
            current_distances[idx] = np.min(distances)

            #setting data for a single object movement 
            ids_POIs[idx] = df_POIs.at[index_min, label_id]
            tag_POIs[idx] = df_POIs.at[index_min, label_POI]   

        df_['id_poi'] = ids_POIs
        df_['dist_poi'] = current_distances
        df_['type_poi'] = tag_POIs
        
        print('Integration with POI was finalized')
        print('\nTotal Time: {:.2f} seconds'.format((time.time() - start_time)))
           
    except Exception as e:
        print('id: {}\n'.format(idx))
        raise e

def join_with_POIs_optimizer(df_, df_POIs, label_id='name', label_POI='POI', dist_poi=[10], reset_index=True):    
    try:
        print('Integration with POIs...')
        start_time = time.time()

        if df_POIs[label_POI].unique() == len(dist_poi):
            ## get a vector with windows time to each point
            if reset_index:
                print('... reseting and dropping index')
                df_.reset_index(drop=True, inplace=True)
                df_POIs.reset_index(drop=True, inplace=True)

            #create numpy array to store new colum to dataframe of movement objects
            current_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
            ids_POIs= np.full(df_.shape[0], np.NAN, dtype='object_')
            tag_POIs = np.full(df_.shape[0], np.NAN, dtype='object_')
        
            
            minimum_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
            shape_POIs = df_POIs.shape[0]
            
            lat_POI = np.full(df_.shape[0], np.NAN, dtype=np.float32)
            lon_POI = np.full(df_.shape[0], np.NAN, dtype=np.float32)
            
            for row in tqdm(df_POIs.itertuples(), total=shape_POIs):   
                idx = row.Index
                #update lat and lot of current index
                lat_POI.fill(row.lat)
                lon_POI.fill(row.lon)
                
                # First iteration is minimum distances 
                if  idx == 0:            
                    minimum_distances = np.float32(ut.distances.haversine(lat_POI, lon_POI, df_['lat'].to_numpy(dtype=np.float32), df_['lon'].to_numpy(dtype=np.float32)))
                    ids_POIs.fill(row.name)
                    tag_POIs.fill(row.POI)
                else:
                    # calcule dist between a POI and ALL tnz
                    current_distances = np.float32(ut.distances.haversine(lat_POI, lon_POI, df_['lat'].to_numpy(dtype=np.float32), df_['lon'].to_numpy(dtype=np.float32)))
                    compare = current_distances < minimum_distances
                    index_True = np.where(compare==True)[0]
                    minimum_distances = np.minimum(current_distances, minimum_distances, dtype=np.float32)       
                    
                    if index_True.shape[0] > 0:                    
                        ids_POIs[index_True] = row.name
                        tag_POIs[index_True] = row.POI

            df_['id_poi'] = ids_POIs        
            df_['dist_poi'] = minimum_distances
            df_['type_poi'] = tag_POIs         
            print('Integration with POI was finalized')
            print('\nTotal Time: {:.2f} seconds'.format((time.time() - start_time)))
        else:
            print('the size of the  dist_poi is different from ')
    except Exception as e:
        print('id: {}\n'.format(idx))
        raise e

def join_with_POIs_by_category(df_, df_POIs, label_category='POI', label_id='name', label_POI='PO+I'):    
    """ Do integration between POIs and TNZ from """
    try:
        print('Integration with POIs...')
        start_time = time.time()
               
        ## get a vector with windows time to each point
        df_.reset_index(drop=True, inplace=True)
        df_POIs.reset_index(drop=True, inplace=True)
        
        #create numpy array to store new colum to dataframe of movement objects
        current_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
        ids_POIs= np.full(df_.shape[0], np.NAN, dtype='object_')
        
        size_categories = df_POIs[label_category].unique()
        print('There are {} categories =============== '.format(len(size_categories)))
        
        for c in size_categories:
            print('Calculing dist to category: {} =============== '.format(c))
            # creating lat and lon array to operation
            df_category = df_POIs[df_POIs[label_category] == c]       
            df_category.reset_index(drop=True, inplace=True)

            for row in tqdm(df_[['lat','lon']].itertuples(), total=df_.shape[0]):
                idx = row.Index
                lat_tnz = np.full(df_category.shape[0], row.lat, dtype=np.float32)
                lon_tnz = np.full(df_category.shape[0], row.lon, dtype=np.float32)

                #calculing distances to 
                distances = ut.distances.haversine(lat_tnz, lon_tnz, df_category['lat'].to_numpy(dtype=np.float32), df_category['lon'].to_numpy(dtype=np.float32))

                # get index to arg_min and min distance
                index_min = np.argmin(distances)

                #setting data for a single object movement
                current_distances[idx] = np.min(distances) 
                ids_POIs[idx] = df_category.at[index_min, label_id]
 
            df_['id_'+c] = ids_POIs
            df_['dist_'+c] = current_distances
        print('Integration with POI was finalized')
        print('\nTotal Time: {:.2f} seconds'.format((time.time() - start_time)))
           
    except Exception as e:
        print('id: {}\n'.format(idx))
        raise e

def join_with_POI_datetime(df_, df_cvp, label_date='datetime', time_window=900, dist_to_poi=50):    
    try:
        print('Integration with CVP...')
        start_time = time.time()
               
        ## get a vector with windows time to each point
        df_.reset_index(drop=True, inplace=True)
        df_cvp.reset_index(drop=True, inplace=True)
        
        #calcule windows time 
        window_starts = df_[label_date] - pd.Timedelta(seconds=time_window)
        window_ends = df_[label_date]  + pd.Timedelta(seconds=time_window)

        #create numpy aux t
        current_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
        event_type = np.full(df_.shape[0], np.NAN, dtype='object_')
        event_id = np.full(df_.shape[0], np.NAN, dtype=np.int32)        
        
        for idx in tqdm(df_.index):
            #filter cvp by datetime
            df_filted = preprocessing.filters.by_datetime(df_cvp, window_starts[idx], window_ends[idx]) 
            size_filter = df_filted.shape[0] 
            
            if(size_filter > 0):
                df_filted.reset_index(drop=True, inplace=True)
                lat_tnz = np.full(size_filter, df_.at[idx, 'lat'], dtype=np.float32)
                lon_tnz = np.full(size_filter, df_.at[idx, 'lon'], dtype=np.float32)
                
                #calcule dist to poi filtred
                distances = ut.distances.haversine(lat_tnz, lon_tnz, df_filted['lat'].to_numpy(dtype=np.float32), df_filted['lon'].to_numpy(dtype=np.float32))
                # get index to arg_min
                index_arg_min = np.argmin(distances)
                # get min distances
                min_distance = np.min(distances)    
                #store data
                current_distances[idx] = min_distance
                #cvp_index = df_filted.index[index_arg_min]
                event_type[idx] = df_filted.at[index_arg_min, 'event_type']   
                event_id[idx] = df_filted.at[index_arg_min, 'event_id']  
                
        df_['event_id_2'] = event_id
        df_['dist_cvp_2'] = current_distances    
        df_['event_type_2'] = event_type 
        print('Integration with CVP was completed')
        print('\nTotal Time: {:.2f} seconds'.format((time.time() - start_time)))
        print('-----------------------------------------------------\n')
    except Exception as e:
        print('id: {}\n'.format(idx))
        raise e

def join_with_POI_datetime_optimizer(df_, df_cvp, label_date='datetime', time_window=900):    
    try:
        print('Integration with CVP...')
        start_time = time.time()
        
        ## get a vector with windows time to each point
        df_.reset_index(drop=True, inplace=True)
        df_cvp.reset_index(drop=True, inplace=True)
        
        #calc window time to each cvp
        window_starts = df_cvp[label_date] - pd.Timedelta(seconds=time_window)
        window_ends = df_cvp[label_date]  + pd.Timedelta(seconds=time_window)

        #create vector to store distances to CVP
        current_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
        event_type = np.full(df_.shape[0], np.NAN, dtype='object_')
        event_id = np.full(df_.shape[0], np.NAN, dtype=np.int32)
        
        minimum_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
        shape_cvp = df_cvp.shape[0]
        for row in tqdm(df_cvp.itertuples(), total=shape_cvp):   
            idx = row.Index
            
            df_filted = preprocessing.filters.by_datetime(df_, window_starts[idx], window_ends[idx])   
           
            size_filter = df_filted.shape[0] 
            
            if(size_filter > 0):
                indexs = df_filted.index               
                #df_filted.reset_index(drop=True, inplace=True)    
                lat_cvp = np.full(df_filted.shape[0], row.lat, dtype=np.float32)
                lon_cvp = np.full(df_filted.shape[0], row.lon, dtype=np.float32)
                
                # First iteration is minimum distances 
                if idx == 0:            
                    minimum_distances[indexs] = ut.distances.haversine(lat_cvp, lon_cvp, df_filted['lat'].to_numpy(dtype=np.float32), df_filted['lon'].to_numpy(dtype=np.float32))
                    event_id[indexs] = row.event_id
                    event_type[indexs] = row.event_type
                else:
                    current_distances[indexs] = ut.distances.haversine(lat_cvp, lon_cvp, df_filted['lat'].to_numpy(dtype=np.float32), df_filted['lon'].to_numpy(dtype=np.float32))
                    compare = current_distances < minimum_distances
                    index_True = np.where(compare==True)[0]
                    
                    minimum_distances = np.minimum(current_distances, minimum_distances)  
                    event_id[index_True] = row.event_id
                    event_type[index_True] = row.event_type
                    
        df_['event_id'] = event_id        
        df_['dist_cvp'] = minimum_distances
        df_['event_type'] = event_type 
        print('Integration with CVP was completed')
        print('\nTotal Time: {:.2f} seconds'.format((time.time() - start_time)))
        print('-----------------------------------------------------\n')

    except Exception as e:
        print('id: {}\n'.format(idx))
        raise e

def join_with_HOME_by_id(df_, df_home, label_id='id', drop_id_without_home=False):
    try:   
        print('Integration with Home...')
        ids_without_home = []

        if df_.index.name is None:
            print('...setting {} as index'.format(label_id))
            df_.set_index(label_id, inplace=True)

        for idx in df_.index.unique():
            filter_home = (df_home[label_id] == idx) 
            
            if df_home[filter_home].shape[0] == 0:
                print('...id: {} has not HOME'.format(idx))
                ids_without_home.append(idx)
            else:
                home = df_home[filter_home].iloc[0]
                lat_tnz = df_.at[idx, 'lat']
                lon_tnz = df_.at[idx, 'lon']

                # if tnz has a single tuple
                if type(lat_tnz) is not np.ndarray:
                    df_.at[idx, 'dist_home'] = ut.distances.haversine(lat_tnz, lon_tnz, home['lat'], home['lon'])
                    df_.at[idx, 'Home'] = home['formatted_address']
                    df_.at[idx, 'city'] = home['city']
                else:
                    lat_home = np.full(df_.loc[idx].shape[0], home['lat'], dtype=np.float32)
                    lon_home = np.full(df_.loc[idx].shape[0], home['lon'], dtype=np.float32)
                    df_.at[idx, 'dist_home'] = ut.distances.haversine(lat_tnz, lon_tnz, lat_home, lon_home)
                    df_.at[idx, 'Home'] = np.array(home['formatted_address'])
                    df_.at[idx, 'city'] = np.array(home['city'])

         
        df_.reset_index(inplace=True)
        print('... Reseting index')

        if drop_id_without_home == True:
            preprocessing.filters.by_id(df_, label_id, ids_without_home)
    except Exception as e:
        print('Erro: idx: {}'.format(idx))
        raise e

def merge_HOME_with_POI(df_, label_dist_poi='dist_poi', label_type_poi='type_poi', label_id_poi = 'id_poi', drop_colums=True):
    try:           
        print('merge home with POI using shortest distance')   
        idx = df_[df_['dist_home'] <= df_[label_dist_poi]].index

        df_.loc[idx, label_type_poi] = 'home'
        df_.loc[idx, label_dist_poi] = df_.loc[idx, 'dist_home']
        df_.loc[idx, label_id_poi] = df_.loc[idx, 'Home']        
        if(drop_colums):
            del df_['Home'], df_['dist_home']
    except Exception as e:
        raise e

"""def integration_CVP_to_tnz(df_, df_cvp, label_date='datetime', time_window=900):    
    try:
        print('Integration with CVP...')
        start_time = time.time()
        
        df_['CVP'] = np.NAN

        #calc window time to each cvp
        window_starts = df_cvp[label_date] - pd.Timedelta(seconds=time_window)
        window_ends = df_cvp[label_date]  + pd.Timedelta(seconds=time_window)

        #create vector to store distances to CVP
        ids_minimum = np.full(df_.shape[0], np.NAN, dtype=np.int64)
        minimum_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
        
        current_ids = np.full(df_.shape[0], np.NAN, dtype=np.int64)
        current_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)

        for i, idx in enumerate(tqdm(df_cvp.index)):    
            #filter tnz by time windows
            df_filted = preprocessing.filters.by_datetime(df_, window_starts[i], window_ends[i])   
            
            size_filter = df_filted.shape[0] 
            
            if(size_filter > 0):
                indexs = df_filted.index
            
                lat_cvp = np.full(df_filted.shape[0], df_cvp.loc[idx]['lat'], dtype=np.float32)
                lon_cvp = np.full(df_filted.shape[0], df_cvp.loc[idx]['lon'], dtype=np.float32)
                
                # First iteration is minimum distances 
                if i == 0:            
                    minimum_distances[indexs] = ut.distances.haversine(lat_cvp, lon_cvp, df_filted['lat'].to_numpy(), df_filted['lon'].to_numpy())
                    ids_minimum[indexs] = df_filted['event_id']
                    print('Minimum distances were calculed')
                    #dic[idx] = minimum_distances
                else:
                    current_distances[indexs] = ut.distances.haversine(lat_cvp, lon_cvp, df_filted['lat'].to_numpy(), df_filted['lon'].to_numpy())
                    current_ids[indexs] = df_filted['event_id']

                    minimum_distances = np.minimum(current_distances, minimum_distances)  
            else:
                print(idx)

        
        df_['CVP'] = minimum_distances    
        df_['id_cvp'] = current_ids        
        print('Integration with CVP was completed')
        print('\nTotal Time: {:.2f} seconds'.format((time.time() - start_time)))
        print('-----------------------------------------------------\n')
        #return dic
    except Exception as e:
        print('id: {}\n'.format(idx))
        raise e

def integration_with_cvp(df_, df_cvp, label_date='datetime', time_window=900, dist_to_cvp=50):    
    try:
        print('Integration with CVP...')
        start_time = time.time()
               
        ## get a vector with windows time to each point
        df_.reset_index(drop=True, inplace=True)
        df_cvp.reset_index(drop=True, inplace=True)
        
        window_starts = df_[label_date] - pd.Timedelta(seconds=time_window)
        window_ends = df_[label_date]  + pd.Timedelta(seconds=time_window)

        current_distances = np.full(df_.shape[0], np.Infinity, dtype=np.float32)
        event_type = np.full(df_.shape[0], np.NAN, dtype='object_')
        event_id = np.full(df_.shape[0], np.NAN, dtype=np.int32)
        for idx in tqdm(df_.index):
            #filter cvp by datetime
            df_filted = preprocessing.filters.by_datetime(df_cvp, window_starts[idx], window_ends[idx]) 
            size_filter = df_filted.shape[0] 
            
            if(size_filter > 0):
                lat_tnz = np.full(size_filter, df_.loc[idx]['lat'], dtype=np.float32)
                lon_tnz = np.full(size_filter, df_.loc[idx]['lon'], dtype=np.float32)
                distances = ut.distances.haversine(lat_tnz, lon_tnz, df_filted['lat'].to_numpy(), df_filted['lon'].to_numpy())
                # get index to arg_min
                index_arg_min = np.argmin(distances)
                # get min distances
                min_distance = min(distances)    
                #store data
                current_distances[idx] = min_distance
                cvp_index = df_filted.index[index_arg_min]
                event_type[idx] = df_cvp.loc[cvp_index]['event_type']   
                event_id[idx] = df_cvp.loc[cvp_index]['event_id']  
        
        df_['event_id'] = event_id
        #df_['event_type'] = event_type
        df_['dist_cvp'] = current_distances     
        print('Integration with CVP was completed')
        print('\nTotal Time: {:.2f} seconds'.format((time.time() - start_time)))
        print('-----------------------------------------------------\n')
    except Exception as e:
        print('id: {}\n'.format(idx))
        raise e

"""