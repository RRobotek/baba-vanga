from prophet import Prophet
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta

def predict(df,
            period: int,
            freq,
            ts_column: str,
            y_column: str):
    """
    Predicts the future values of the given dataframe

    @param df: dataframe with the known data
    @param period: number of periods to predict
    @param freq: frequency of the prediction
    @param ts_column: name of the column with the timestamp
    @param y_column: name of the column with the values to predict
    """

    df_prophet = df.rename(columns={ts_column: 'ds', y_column: 'y'})

    model = Prophet()
    model.fit(df_prophet)

    future = model.make_future_dataframe(periods=period, freq=freq)

    forecast = model.predict(future)
    predicted_data = forecast.tail(period)

    #predicted_data['ds'] = predicted_data['ds'].dt.tz_localize(pytz.utc)#.astype(str)

    # make prediction and training data continuous by 
    # setting the ds of the first predicted value to the last known value close
    predicted_data['yhat'].iloc[0] = df[y_column].iloc[-1]

    return predicted_data

if __name__ == '__main__':
    df = pd.read_csv("data.csv")
    #print(df.info())

    predicted_data = predict(df, 60, timedelta(minutes=5))

    # make prediction and training data continuous by 
    # settings the ds of the first predicted value to the last known value close
    # predicted_data['yhat'].iloc[0] = df['close'].iloc[-1]

    print("\nKNOWN")   
    print(df.iloc[-1])
    print("\nPREDICTED")
    print(predicted_data.iloc[0:1])

    # plot with plt
    plt.plot(df['timestamp'], df['close'], color='black', label='Known Data')
    plt.plot(predicted_data['ds'], predicted_data['yhat'], color='blue', label='Predicted Values')

    plt.plot(predicted_data['ds'], predicted_data['yhat_upper'], color='green', linestyle='dashed', label='Upper Bound')
    plt.plot(predicted_data['ds'], predicted_data['yhat_lower'], color='red', linestyle='dashed', label='Lower Bound')

    plt.xlabel('Timestamp')
    plt.ylabel('Closed Price')
    plt.title('Known Data and Predicted Values')

    plt.legend()
    plt.savefig('graph_new.png')
    plt.show()
