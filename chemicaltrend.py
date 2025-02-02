import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import pymannkendall as mk
import os
import requests

# 🚀 لینک مستقیم فایل در گیت‌هاب
GITHUB_RAW_URL = "https://media.githubusercontent.com/media/darksky16/Chemicaltrend/refs/heads/main/combined_chemical_test.csv"

# 🔽 دانلود فایل به‌صورت مستقیم و ذخیره در سرور
csv_file = "combined_chemical_test.csv"
if not os.path.exists(csv_file):
    response = requests.get(GITHUB_RAW_URL)
    if response.status_code == 200:
        with open(csv_file, "wb") as f:
            f.write(response.content)
        print("✅ CSV file downloaded successfully from GitHub!")
    else:
        print(f"❌ Failed to download CSV file. Status code: {response.status_code}")

# 📌 لیست ستون‌هایی که نیاز داریم
usecols = ['ostan', 'UTM', 'gregorian_date', 'na', 'k', 'mg', 'ca', 'so4', 'cl', 'hco3', 'co3', 'no3', 'ph', 'tds', 'ec']

# 🏆 پردازش داده‌ها در **قطعات کوچک** برای جلوگیری از کرش
chunk_size = 100000  # پردازش 100,000 ردیف در هر بار
chunks = []

for chunk in pd.read_csv(csv_file, encoding='utf-8-sig', low_memory=True, usecols=usecols, chunksize=chunk_size):
    chunk['gregorian_date'] = pd.to_datetime(chunk['gregorian_date'], errors='coerce')
    chunk = chunk.dropna(subset=['gregorian_date'])  # حذف داده‌های بدون تاریخ
    chunks.append(chunk)

# ✅ ترکیب تمام چانک‌ها در یک DataFrame
df = pd.concat(chunks, ignore_index=True)
print(f"✅ Loaded {len(df)} rows successfully!")

# 🎯 مقداردهی اولیه به Dash
app = dash.Dash(__name__)

# 🎨 رابط کاربری برنامه
app.layout = html.Div([
    html.H1("تحلیل روند مواد شیمیایی", style={'textAlign': 'center'}),

    # انتخاب استان
    html.Div([
        html.Label("انتخاب استان:"),
        dcc.Dropdown(
            id='province-filter',
            options=[{'label': province, 'value': province} for province in sorted(df['ostan'].dropna().unique())],
            multi=True,
            placeholder="استان را انتخاب کنید"
        ),
    ], style={'width': '50%', 'padding': '10px'}),

    # انتخاب UTM
    html.Div([
        html.Label("انتخاب کد UTM:"),
        dcc.Dropdown(id='utm-filter', multi=True, placeholder="UTM را انتخاب کنید"),
    ], style={'width': '50%', 'padding': '10px'}),

    # نمایش محدوده
    html.Div([
        html.Label("محدوده انتخابی:"),
        html.Div(id='mahdoodeh-display', style={'padding': '10px', 'border': '1px solid #ccc', 'width': '50%'}),
    ]),

    # انتخاب متغیر شیمیایی
    html.Div([
        html.Label("انتخاب متغیر شیمیایی:"),
        dcc.Dropdown(
            id='variable-filter',
            options=[{'label': var, 'value': var} for var in usecols if var not in ['ostan', 'UTM', 'gregorian_date']],
            value='na',  # مقدار پیش‌فرض
            placeholder="متغیر مورد نظر را انتخاب کنید"
        ),
    ], style={'width': '50%', 'padding': '10px'}),

    # نمودار
    dcc.Graph(id='chemical-trend-plot'),

    # تحلیل آماری
    html.Div([
        html.Label("تحلیل آماری Mann-Kendall و Sen’s Slope:"),
        html.Div(id='trend-analysis-display', style={'padding': '10px', 'border': '1px solid #ccc', 'width': '80%'}),
    ]),

    # خلاصه سطح استان
    html.Div([
        html.Label("خلاصه تحلیل سطح استان:"),
        html.Div(id='province-summary-display', style={'padding': '10px', 'border': '1px solid #ccc', 'width': '80%'}),
    ]),
])

# 🔄 بروز رسانی لیست UTM بر اساس استان انتخابی
@app.callback(
    Output('utm-filter', 'options'),
    Input('province-filter', 'value')
)
def update_utm_dropdown(selected_provinces):
    if not selected_provinces:
        return []
    filtered_df = df[df['ostan'].isin(selected_provinces)]
    return [{'label': f"{utm} (تعداد داده‌ها: {len(filtered_df[filtered_df['UTM'] == utm])})", 'value': utm}
            for utm in filtered_df['UTM'].dropna().unique()]

# نمایش محدوده برای UTM انتخاب شده
@app.callback(
    Output('mahdoodeh-display', 'children'),
    Input('utm-filter', 'value')
)
def update_mahdoodeh_display(selected_utms):
    if not selected_utms:
        return "هیچ UTM انتخاب نشده است"
    return ', '.join(df.loc[df['UTM'].isin(selected_utms), 'ostan'].dropna().unique())

# 🔄 بروز رسانی نمودار و تحلیل آماری
@app.callback(
    [Output('chemical-trend-plot', 'figure'),
     Output('trend-analysis-display', 'children'),
     Output('province-summary-display', 'children')],
    [Input('province-filter', 'value'),
     Input('utm-filter', 'value'),
     Input('variable-filter', 'value')]
)
def update_plot_and_analysis(selected_provinces, selected_utms, selected_variable):
    if not selected_provinces:
        return px.line(title="هیچ استانی انتخاب نشده است"), "هیچ استانی انتخاب نشده است", "هیچ استانی انتخاب نشده است"

    filtered_df = df[df['ostan'].isin(selected_provinces)]
    if selected_utms:
        filtered_df = filtered_df[filtered_df['UTM'].isin(selected_utms)]

    if filtered_df.empty:
        return px.line(title="داده‌ای موجود نیست"), "داده‌ای موجود نیست", "داده‌ای موجود نیست"

    # رسم نمودار
    fig = px.line(
        filtered_df,
        x='gregorian_date',
        y=selected_variable,
        color='UTM',
        title=f"روند {selected_variable} بر اساس استان و UTM",
        labels={'gregorian_date': 'تاریخ میلادی', selected_variable: selected_variable},
        template='plotly'
    )
    fig.update_traces(mode='lines+markers')

    # تحلیل آماری
    analysis_results = []
    for utm in selected_utms:
        utm_data = filtered_df[filtered_df['UTM'] == utm][selected_variable].dropna().values
        if len(utm_data) < 5:
            continue
        mk_result = mk.original_test(utm_data)
        trend = "صعودی" if mk_result.z > 0 else "نزولی"
        significance = "معنی‌دار" if mk_result.p < 0.05 else "غیرمعنی‌دار"
        analysis_results.append(f"UTM: {utm}, روند: {trend}, معنی‌داری: {significance}")

    return fig, html.Div(analysis_results), f"تعداد داده‌ها: {len(filtered_df)}"

# 🚀 اجرای برنامه
if __name__ == '__main__':
    app.run_server(debug=True)
