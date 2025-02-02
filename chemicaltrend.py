import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import pymannkendall as mk
import os

# مسیر صحیح برای خواندن فایل در محیط Railway
csv_file = os.path.join(os.path.dirname(__file__), "combined_chemical_test.csv")
df = pd.read_csv(csv_file, encoding='utf-8-sig', low_memory=False)

# اطمینان از این که ستون تاریخ در فرمت صحیح است
df['gregorian_date'] = pd.to_datetime(df['gregorian_date'], errors='coerce')
df = df.dropna(subset=['gregorian_date'])

# لیست متغیرهای شیمیایی مورد بررسی
chemical_variables = ['k', 'na', 'mg', 'ca', 'so4', 'cl', 'hco3', 'co3', 'no3', 'ph', 'tds', 'ec']

# مقداردهی اولیه به Dash
app = dash.Dash(__name__)

# رابط کاربری برنامه
app.layout = html.Div([
    html.H1("آنالیز روند مواد شیمیایی", style={'textAlign': 'center'}),

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

    # انتخاب UTM (دینامیک)
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
            options=[{'label': var, 'value': var} for var in chemical_variables],
            value='na',  # مقدار پیش‌فرض (سدیم)
            placeholder="متغیر مورد نظر را انتخاب کنید"
        ),
    ], style={'width': '50%', 'padding': '10px'}),

    # نمودار
    dcc.Graph(id='chemical-trend-plot'),

    # تحلیل آماری مان-کندال و شیب سن
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

# بروز رسانی لیست UTM بر اساس استان انتخابی
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
    mahdoodeh_list = df.loc[df['UTM'].isin(selected_utms), 'mahdoodeh'].dropna().unique()
    return ', '.join(mahdoodeh_list) if len(mahdoodeh_list) > 0 else "محدوده‌ای یافت نشد"

# بروز رسانی نمودار و تحلیل آماری
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

    # اطمینان از این که متغیر شیمیایی معتبر است
    if not selected_variable:
        selected_variable = chemical_variables[0]

    # اطمینان از این که UTM خالی نیست
    if not selected_utms:
        selected_utms = []

    filtered_df = df[df['ostan'].isin(selected_provinces)]

    # خلاصه سطح استان
    utm_groups = filtered_df.groupby('UTM')
    significant_count = 0
    nonsignificant_count = 0
    total_utm = len(utm_groups)

    for utm, group in utm_groups:
        values = group[selected_variable].dropna().values
        if len(values) < 5:
            continue
        mk_result = mk.original_test(values)
        if mk_result.p < 0.05:
            significant_count += 1
        else:
            nonsignificant_count += 1

    ratio = significant_count / nonsignificant_count if nonsignificant_count > 0 else float("inf")

    province_summary = (f"مجموع UTMها: {total_utm}, "
                        f"دارای روند معنی‌دار: {significant_count} "
                        f"({(significant_count / total_utm) * 100:.2f}%), "
                        f"بدون روند: {nonsignificant_count} "
                        f"({(nonsignificant_count / total_utm) * 100:.2f}%), "
                        f"نسبت (رونددار:بدون روند): {ratio:.2f}")

    # فیلتر برای UTM انتخاب شده
    if selected_utms:
        filtered_df = filtered_df[filtered_df['UTM'].isin(selected_utms)]

    if filtered_df.empty:
        return px.line(title="داده‌ای موجود نیست"), "داده‌ای موجود نیست", province_summary

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

    # تحلیل سطح UTM
    analysis_results = []
    for utm in selected_utms:
        utm_data = filtered_df[filtered_df['UTM'] == utm][selected_variable].dropna().values
        if len(utm_data) < 5:
            analysis_results.append(f"UTM: {utm} - داده کافی نیست")
            continue

        mk_result = mk.original_test(utm_data)
        trend = "صعودی" if mk_result.z > 0 else "نزولی"
        significance = "معنی‌دار" if mk_result.p < 0.05 else "غیرمعنی‌دار"

        analysis_results.append(f"UTM: {utm}, روند: {trend}, معنی‌داری: {significance}")

    return fig, html.Div(analysis_results), province_summary

if __name__ == '__main__':
    app.run_server(debug=True)
