import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="India Housing Insights",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏡 India Housing Insights")
st.caption("Explore residential property prices, locations, property features and availability across India.")

DEFAULT_FILE = "india_housing_prices(2).csv"

@st.cache_data(show_spinner="Loading housing data...")
def load_data(file):
    data = pd.read_csv(file)
    # Normalize common text fields for reliable filtering.
    for col in data.select_dtypes(include="object").columns:
        data[col] = data[col].astype("string").str.strip()
    return data

uploaded = st.sidebar.file_uploader(
    "Upload housing CSV (optional)",
    type=["csv"],
    help="If you do not upload a file, the bundled dataset is used."
)

try:
    if uploaded is not None:
        df = load_data(uploaded)
        source_label = uploaded.name
    else:
        df = load_data(DEFAULT_FILE)
        source_label = DEFAULT_FILE
except FileNotFoundError:
    st.error(f"Dataset not found: {DEFAULT_FILE}. Keep the CSV in the same folder as app.py or upload it in the sidebar.")
    st.stop()
except Exception as exc:
    st.error(f"Could not read the CSV: {exc}")
    st.stop()

required = ["State", "City", "Property_Type", "BHK", "Size_in_SqFt", "Price_in_Lakhs"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error("The uploaded file is missing required columns: " + ", ".join(missing))
    st.stop()

st.sidebar.header("🔎 Filters")
states = sorted(df["State"].dropna().astype(str).unique())
chosen_states = st.sidebar.multiselect("State", states, default=states)
state_df = df[df["State"].astype(str).isin(chosen_states)]

cities = sorted(state_df["City"].dropna().astype(str).unique())
chosen_cities = st.sidebar.multiselect("City", cities, default=cities)
city_df = state_df[state_df["City"].astype(str).isin(chosen_cities)]

types = sorted(city_df["Property_Type"].dropna().astype(str).unique())
chosen_types = st.sidebar.multiselect("Property type", types, default=types)
filtered = city_df[city_df["Property_Type"].astype(str).isin(chosen_types)]

if "BHK" in filtered.columns and not filtered.empty:
    min_bhk = int(filtered["BHK"].min())
    max_bhk = int(filtered["BHK"].max())
    bhk_range = st.sidebar.slider("BHK range", min_bhk, max_bhk, (min_bhk, max_bhk))
    filtered = filtered[filtered["BHK"].between(*bhk_range)]

if "Price_in_Lakhs" in filtered.columns and not filtered.empty:
    low = float(filtered["Price_in_Lakhs"].min())
    high = float(filtered["Price_in_Lakhs"].max())
    if low < high:
        price_range = st.sidebar.slider(
            "Price range (₹ lakhs)", low, high, (low, high), step=max((high-low)/100, 0.01)
        )
        filtered = filtered[filtered["Price_in_Lakhs"].between(*price_range)]

if filtered.empty:
    st.warning("No properties match the selected filters. Widen the filters to see results.")
    st.stop()

# Numeric measures
price = pd.to_numeric(filtered["Price_in_Lakhs"], errors="coerce")
size = pd.to_numeric(filtered["Size_in_SqFt"], errors="coerce")
avg_price = price.mean()
median_price = price.median()
avg_size = size.mean()
records = len(filtered)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Properties", f"{records:,}")
c2.metric("Average price", f"₹{avg_price:,.2f} L" if pd.notna(avg_price) else "N/A")
c3.metric("Median price", f"₹{median_price:,.2f} L" if pd.notna(median_price) else "N/A")
c4.metric("Average size", f"{avg_size:,.0f} sq.ft." if pd.notna(avg_size) else "N/A")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Market overview", "📍 Location analysis", "🏠 Property details", "🧹 Data quality"])

with tab1:
    left, right = st.columns(2)
    with left:
        price_city = (filtered.groupby("City", dropna=True)["Price_in_Lakhs"]
                      .median().sort_values(ascending=False).head(15).reset_index())
        fig = px.bar(price_city, x="City", y="Price_in_Lakhs",
                     title="15 cities with highest median listing price",
                     labels={"Price_in_Lakhs": "Median price (₹ lakhs)"})
        fig.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.histogram(filtered, x="Price_in_Lakhs", nbins=40,
                           title="Distribution of property prices",
                           labels={"Price_in_Lakhs": "Price (₹ lakhs)"})
        st.plotly_chart(fig, use_container_width=True)

    if "Property_Type" in filtered.columns:
        type_summary = (filtered.groupby("Property_Type", dropna=False)
                        .agg(Properties=("Price_in_Lakhs", "size"),
                             Median_Price=("Price_in_Lakhs", "median"))
                        .reset_index())
        fig = px.bar(type_summary, x="Property_Type", y="Median_Price", color="Property_Type",
                     title="Median price by property type",
                     labels={"Median_Price": "Median price (₹ lakhs)"})
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    city_summary = (filtered.groupby(["State", "City"], dropna=False)
                    .agg(Properties=("Price_in_Lakhs", "size"),
                         Average_Price=("Price_in_Lakhs", "mean"),
                         Median_Price=("Price_in_Lakhs", "median"))
                    .reset_index().sort_values("Properties", ascending=False))
    st.subheader("City-level comparison")
    st.dataframe(city_summary, use_container_width=True, hide_index=True)
    if not city_summary.empty:
        fig = px.scatter(city_summary, x="Properties", y="Median_Price",
                         size="Properties", color="State", hover_name="City",
                         title="Property volume vs median price by city",
                         labels={"Median_Price": "Median price (₹ lakhs)"})
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    left, right = st.columns(2)
    with left:
        if "BHK" in filtered.columns:
            bhk_counts = filtered["BHK"].value_counts().sort_index().rename_axis("BHK").reset_index(name="Properties")
            fig = px.bar(bhk_counts, x="BHK", y="Properties", title="Properties by BHK")
            st.plotly_chart(fig, use_container_width=True)
    with right:
        if "Furnished_Status" in filtered.columns:
            furnished = filtered["Furnished_Status"].value_counts(dropna=False).rename_axis("Furnishing").reset_index(name="Properties")
            fig = px.pie(furnished, names="Furnishing", values="Properties", title="Furnishing status")
            st.plotly_chart(fig, use_container_width=True)

    feature_cols = [c for c in ["Public_Transport_Accessibility", "Parking_Space",
                                "Security", "Availability_Status", "Owner_Type"]
                    if c in filtered.columns]
    if feature_cols:
        selected_feature = st.selectbox("Compare properties by feature", feature_cols)
        feature_summary = (filtered.groupby(selected_feature, dropna=False)
                           .agg(Properties=("Price_in_Lakhs", "size"),
                                Median_Price=("Price_in_Lakhs", "median"))
                           .reset_index())
        fig = px.bar(feature_summary, x=selected_feature, y="Median_Price",
                     title=f"Median price by {selected_feature}",
                     labels={"Median_Price": "Median price (₹ lakhs)"})
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Dataset checks")
    missing_counts = df.isna().sum().sort_values(ascending=False)
    duplicates = int(df.duplicated().sum())
    d1, d2, d3 = st.columns(3)
    d1.metric("Rows in source dataset", f"{len(df):,}")
    d2.metric("Duplicate rows", f"{duplicates:,}")
    d3.metric("Columns", f"{df.shape[1]:,}")
    missing_table = missing_counts[missing_counts > 0].rename("Missing values").reset_index()
    missing_table.columns = ["Column", "Missing values"]
    if missing_table.empty:
        st.success("No missing values were detected in the source dataset.")
    else:
        st.dataframe(missing_table, use_container_width=True, hide_index=True)
    st.caption("These checks report missing and duplicate values; they do not automatically delete records.")

st.divider()
st.subheader("Filtered property records")
st.caption(f"Data source: {source_label} · Showing {len(filtered):,} matching rows")
st.dataframe(filtered.head(1000), use_container_width=True, hide_index=True)
csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download filtered data as CSV",
    data=csv_bytes,
    file_name="filtered_india_housing_data.csv",
    mime="text/csv"
)

st.caption("Note: This dashboard describes the records in the supplied dataset. Prices are not independently verified market valuations.")
