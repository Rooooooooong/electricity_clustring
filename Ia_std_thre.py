import numpy as npimport pandas as pdimport matplotlib as mplimport matplotlib.pyplot as pltfrom datetime import datetimeimport mathpd.options.mode.chained_assignment = Noneimport randompd.set_option('display.max_columns',10)def data_preprocess(data):    '''    Preprocess data in order to calculate threshold    Input:        data: DataFrame        columns: [TimeStr, Ia]    Output:        data: DataFrame        columns: [time, Ia]    '''    data = data[['TimeStr', 'Ia']]    data.loc[:,'TimeStr'] = pd.to_datetime(data['TimeStr'])    data.reset_index(drop=True, inplace=True)#删除日期缺失值    # data.loc[data['Ia'] > 1000, 'Ia'] = -1    data.dropna(subset=['TimeStr'], inplace=True)    if len(data) == 0:        return data#处理日期重复    data.loc[:,'TimeStr']=pd.to_datetime(data['TimeStr'].apply(lambda x: datetime.strftime(x, format='%Y-%m-%d %H:%M:%S')))    data.drop_duplicates('TimeStr', inplace=True)    data.reset_index(drop=True, inplace=True)#日期补全    time_series = pd.date_range(data["TimeStr"].min(), data["TimeStr"].max(), freq='s')    ts = pd.DataFrame(time_series, columns=["time"])    data = data.merge(ts, how='right', left_on="TimeStr", right_on="time")    data.drop(['TimeStr'], axis=1, inplace=True)    data.sort_values(by='time', inplace=True)    data.reset_index(drop=True, inplace=True)    data['Ia'] = data['Ia'].rolling(window=5, min_periods=1, center=False).median()    data.fillna(-1, inplace=True)    data = data[['time', 'Ia']]    '''    data['time','Ia']    '''    return datadef  hampel(val_orig,k=5,t0=3):    vals=val_orig.loc[:,'Ia']    # Hampel Filter    L = 1.4826    rolling_median=vals.rolling(window=k,min_periods=1,center=True).median()    difference=np.abs(rolling_median-vals)    median_abs_deviation=difference.rolling(window=k,min_periods=1,center=False).median()    threshold=t0*L*median_abs_deviation    outlier_idx=difference>threshold    val_orig.loc[outlier_idx,'Ia']=rolling_median[outlier_idx]    val_orig.loc[:,'Ia'].fillna(-1,inplace=True)    val_orig = val_orig[['time', 'Ia']]    return val_origdef window_fun(k,data,low,flag=False):    global Data,len_win_count# ## low=0.1# k=5    Data=data_preprocess(data)        # Data=hampel(Data)    Data = Data.drop(Data[Data['Ia'] <=low].index).reset_index(drop=True)  #删除-1 0    if len(Data)==0:        print('电流值全部小于%s' % low)        standby_Ia_max, standby_Ia_min, standby_Ia_median=0,0,0        return standby_Ia_max,standby_Ia_min,standby_Ia_median,Data    if flag==True:        l_cv=list(range(k*60))        m=random.sample(l_cv,1)[0]        Data['no']=pd.Series(range(0,len(Data)))+m        Data['window_no']=Data['no']//(k*60)        Data['no'] = pd.Series(range(0, len(Data)))    else:        Data['no'] = pd.Series(range(0, len(Data)))        Data['window_no'] = Data['no'] // (k * 60)    Data['count']=1    Iamean=round(Data.groupby(['window_no'])['Ia'].mean().reset_index(drop=False),1)    Iamean=Iamean.rename(columns={"Ia":"Ia_mean"})    Iastd=round(Data.groupby(['window_no'])['Ia'].std().reset_index(drop=False),1)    Iastd=Iastd.rename(columns={"Ia": "Ia_std"})    Data=Data.merge(Iamean,how='left',on='window_no')    Data=Data.merge(Iastd,how='left',on='window_no')    #先按照std升序排列，再按照Ia_mean升序排列    Data_new=pd.DataFrame(Data.groupby(['Ia_mean','Ia_std'])['count'].sum().reset_index(drop=False))    Data_new['window_count']=Data_new['count']/(60*5)  #最后一组不满一个 60*5 的整数倍    #可以对标准差在0.2以下的 一视同仁    Data_new_nostd=Data_new.loc[Data_new['Ia_std']<0.2,:].reset_index(drop=True)    Data_new_nostd=Data_new_nostd.groupby(['Ia_mean'])['window_count'].sum().reset_index(drop=False)    Data_new_nostd['window_prob']=Data_new_nostd['window_count']/Data_new_nostd['window_count'].sum()    len_win_count=Data_new_nostd['window_count'].sum()    # cdf    # for i in range(0, len(Data_new_nostd)):    #     Data_new_nostd.loc[i, 'cdf_prob'] = Data_new_nostd.loc[:i, 'window_prob'].sum()    standby_Ia_min1, standby_Ia_min2=Data_new_nostd.loc[:1,'Ia_mean']    standby_Ia_max=Data_new_nostd['Ia_mean'].max()    # 计算每个区块的初始位置    d1 = Data[['no', 'window_no', 'Ia_mean', 'Ia_std']].drop_duplicates('window_no').reset_index(drop=True)    d1 = d1.rename(columns={'no': 'left_start'})    left_loc = d1[d1['Ia_std'] < 0.2].reset_index(drop=True)    data_thre=Data_new_nostd['Ia_mean'].values    thre_dict={}  #存放所有的准阈值 以及其对应的 区间起始位置（这里删除了std>=0.2的电流的阈值)    for i in range(len(data_thre)):        thre_dict.setdefault(data_thre[i])        left_iter = left_loc.loc[left_loc['Ia_mean'] == data_thre[i], 'left_start'].values        thre_dict[data_thre[i]]=left_iter    return standby_Ia_min1, standby_Ia_min2,standby_Ia_max,Data_new_nostd,thre_dictdef entropy_down_fun(data_new_nostd,thre_dict,k=5):    len_stand=k*60    thre_data=pd.DataFrame({'thre':list(thre_dict.keys())})    down_num_list=[]    entropy_list=[]    for i in list(thre_dict.keys()):        curent_value=i        # print(curent_value)        down_one=[]        entropy_one=[]        for j in range(len(thre_dict[curent_value])):            idx = thre_dict[curent_value][j]            idx_end=min((idx+len_stand-1),len(Data))  #最后一个波特殊处理            curent_data=Data.loc[idx:idx_end,'Ia']            up_ratio=(curent_data>curent_value).sum()/len(curent_data)+0.001 #防止出现0            down_ratio=1-up_ratio            down_one.append((curent_data<=curent_value).sum())            entropy=down_ratio*np.log2(down_ratio)+up_ratio*np.log2(up_ratio)            k=math.ceil(len_win_count)            entropy_one.append(entropy/k)        down_num_list.append(pd.Series(down_one).sum())        entropy_list.append(-pd.Series(entropy_one).sum())    thre_data['down_ratio']=down_num_list    thre_data['entropy_list']=entropy_list    # print(thre_data)    Data_result=data_new_nostd.merge(thre_data,how='left',left_on='Ia_mean',right_on='thre')    return Data_resultdef plot_fun(data, standby_Ia_min1, standby_Ia_min2,standby_Ia_max):    ax=plt.figure(figsize=(10,8),num=1)    plt.plot(data['Ia'],linewidth=0.5,color='coral',linestyle=':',marker='.',markersize=0.3)    plt.axhline(y=standby_Ia_min1, linewidth=1.5, color='cornflowerblue')    plt.axhline(y=standby_Ia_min2,linewidth=1.5,color='royalblue')    plt.axhline(y=standby_Ia_max, linewidth=1, color='gray')    #ax.savefig(output+'test1.png')    plt.show()def cross_validation(data,k=5,n_folds=5):    s=[]    least_common=[]    for i in range(5):        random.seed(2018+i)        _,_,_,nostd,thre_dict=window_fun(k,data,0.1,flag=True)        # data_result=entropy_down_fun(nostd, thre_dict, k=5)        s.append(nostd)        least_common.append(len(nostd))        # print(nostd)    sum=0    lc=min(least_common)    for i in range(5):        sum+=s[i].loc[0:(lc-1),:]/5    return sumdef select_count_thre(cv_result,k=1):    length=len(cv_result)    if k==0:        print('请输入大于0的k')    else:        k=k-1    max_num=cv_result.sort_values(by='window_count',ascending=False).reset_index(drop=False).loc[0:min(math.ceil(length/2),k),]    return max_num[['Ia_mean', 'window_count']]def select_var_thre(cv_result,base_Ia):    l_all_Ia = cv_result['Ia_mean'].tolist()    # base_Ia = base_Ia['Ia_mean'].tolist()    for x in base_Ia:        l_all_Ia.remove(x)    choice_Ia=[]    for i in range(len(l_all_Ia)):        temp = base_Ia.copy()        temp.append(l_all_Ia[i])        choice_Ia.append(np.var(temp))    max_var_idx=pd.Series(choice_Ia).idxmax()    base_Ia.append(l_all_Ia[max_var_idx])    return base_Iadef add_thre(cv_result,base_k,add_k):    base_Ia = select_count_thre(cv_result, base_k)['Ia_mean'].tolist() #输入转化    for i in range(add_k):        base_Ia=select_var_thre(cv_result,base_Ia)        print('-'*25+'第i次选择阈值: %s' %base_Ia[-1] +'-'*25)    print('最终选择的阈值:%s' %base_Ia)    Ia_thre=pd.DataFrame({'Ia_thre':base_Ia})    out_report=Ia_thre.merge(cv_result,how='left',left_on='Ia_thre',right_on='Ia_mean')    out_report=out_report.drop(columns='Ia_mean')    return out_reportdef graph_fun(data,out_report):    length=len(out_report)    ax = plt.figure(figsize=(10, 8), num=1)    plt.plot(data['Ia'], linewidth=0.5, color='slategrey', linestyle=':', marker='.', markersize=0.3)    # color_list=['tan','lightblue','rosybrown','darkcyan','tomato','orchid','indianred','olive','indigo']    color_list=[plt.cm.tab20c(each) for each in np.linspace(0,1,10)]    thre = round(out_report['Ia_thre'], 2)    prob = round(out_report['window_prob'], 4) * 100    for i in range(length):         plt.axhline(y=thre[i], linewidth=1.5, color=color_list[i], label='thre:%s\nwindow:%s %%' % (thre[i],prob[i]))    # ax.savefig(output+'test1.png')    plt.title('Threshold Recommended',fontsize=20)    plt.legend()    plt.show()if __name__=="__main__":    # data=pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.15.203.11.csv')    # data=pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.8.182.61.csv')    # data = pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.9.129.93.csv')    # data = pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.9.129.78.csv')    #    # data = pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.9.130.99.csv')    # data = pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.9.130.110.csv')    data = pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.9.129.79.csv')    #    # data = pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.9.129.167.csv')    # 等离子切割机    # data = pd.read_csv(r'C:\Users\rongjin.wang\Desktop\10.9.129.169_0802.csv')    # data = pd.read_pickle(r'C:\Users\rongjin.wang\Desktop\10.9.129.97.pkl')    # data = pd.read_pickle(r'C:\Users\rongjin.wang\Desktop\10.9.129.94.pkl')    data_plot = data.copy()    standby_Ia_min1, standby_Ia_min2, standby_Ia_max,Data_new_nostd,thre_dict=window_fun(5, data,0.1)    Data_result=entropy_down_fun(Data_new_nostd,thre_dict,k=5)    cv_result=cross_validation(data)    print('='*20+'cv_result'+'='*20)    print('-'*20+'cv滑窗'+'-'*20)    print(cv_result)    print('=' * 20 + 'thre_result' + '=' * 20)    print('-' * 20 + '根据需要取阈值' + '-' * 20)    out_report = add_thre(cv_result, base_k=2, add_k=2)    print(out_report)    print('=' * 20 + 'thre' + '=' * 20)    print('-' * 20 + '传参画图' + '-' * 20)    thre = tuple(out_report['Ia_thre'])    # win_prob=tuple(out_report['window_prob'])    print(thre)    graph_fun(data_plot,out_report)    # plot_fun(data_plot, standby_Ia_min1, standby_Ia_min2, standby_Ia_max)