d3.json('/summarydata').then(json_data => {
  const now = Date.now();
  const right = new Date(now);
  const hourly_left = new Date(now).setDate(right.getDate() - 7);
  const daily_left = new Date(now).setDate(right.getDate() - 30);
  const monthly_left = new Date(now).setDate(right.getDate() - 365);

  const hourly_records = json_data.map(x=>{
    return {
      time:x[0]/1e6,
      load:x[1],
      measure:+x[2]
    };
  });

  const hourly_window = hourly_records.filter(x=>x.time>hourly_left);

  const load_groups_hourly_records = d3.groups(hourly_window, d=>d.load)
  load_groups_hourly_records.sort((a,b)=>d3.ascending(a[0],b[0]));

  const hourly_by_load = load_groups_hourly_records.map(x => x[1]);

  const daily_window = hourly_records.filter(x=>x.time>daily_left);
  const hourly_truncated_to_day = daily_window.map(x=>{
    t = new Date(x.time);
    t.setHours(0,0,0,0);
    return {
      time:t.valueOf(),
      load:x.load,
      measure:x.measure
    };
  });
  const daily_rollup = d3.rollups(hourly_truncated_to_day,
    v=>d3.sum(v, d=>d.measure), d=>d.load, d=>d.time);
  daily_rollup.sort((a,b)=>d3.ascending(a[0],b[0]));
  const daily_by_load = daily_rollup.map(x => x[1]).map(x=>
    x.map(y=>{
      return {
        time:y[0],
        measure:y[1]
      };
    }
  ));

  const monthly_window = hourly_records.filter(x=>x.time>monthly_left);
  const hourly_truncated_to_month = monthly_window.map(x=>{
    t = new Date(x.time);
    t.setHours(0,0,0,0);
    t.setDate(0);
    return {
      time:t.valueOf(),
      load:x.load,
      measure:x.measure
    };
  });
  const monthly_rollup = d3.rollups(hourly_truncated_to_month,
    v=>d3.sum(v, d=>d.measure), d=>d.load, d=>d.time);
  monthly_rollup.sort((a,b)=>d3.ascending(a[0],b[0]));
  const monthly_by_load = monthly_rollup.map(x => x[1]).map(x=>
    x.map(y=>{
      return {
        time:y[0],
        measure:y[1]
      };
    }
  ));

  const line = fc
    .seriesSvgLine()
    .crossValue(d => new Date(d.time))
    .mainValue(d => d.measure);

  const color = d3.scaleOrdinal(d3.range(hourly_by_load.length),
    d3.schemeCategory10);

  const series = fc.seriesSvgRepeat()
    .orient('horizontal')
    .series(line)
    .decorate(sel => { sel.attr('stroke', (_, i) => color(i)); });

  const legend = d3.legendColor()
    .shapeWidth(30)
    .orient('vertical')
    .scale(color)
    .labels(load_groups_hourly_records.map(x => x[0]));

  const hourly_chart = fc.chartCartesian(d3.scaleTime(), d3.scaleLinear())
    .chartLabel('kWh by hour (7d)')
    .xDomain(
      fc.extentTime()
        .accessors([d => new Date(d.time)])(hourly_by_load.flat()))
    .yDomain(
      fc.extentLinear()
        .include([0])
        .accessors([d => d.measure])(hourly_by_load.flat()))
    .yLabel('kilowatt-hours')
    .yOrient('left')
    .svgPlotArea(series);

  d3.select('div#hourly')
    .datum(hourly_by_load)
    .call(hourly_chart)
    .select('d3fc-group d3fc-svg.plot-area svg')
    .call(legend);

  const daily_chart = fc.chartCartesian(d3.scaleTime(), d3.scaleLinear())
    .chartLabel('kWh by day (30d)')
    .xDomain(
      fc.extentTime()
        .accessors([d => new Date(d.time)])(daily_by_load.flat()))
    .yDomain(
      fc.extentLinear()
        .include([0])
        .accessors([d => d.measure])(daily_by_load.flat()))
    .yLabel('kilowatt-hours')
    .yOrient('left')
    .svgPlotArea(series);

  d3.select('div#daily')
    .datum(daily_by_load)
    .call(daily_chart)
    .select('d3fc-group d3fc-svg.plot-area svg')
    .call(legend);

  const monthly_chart = fc.chartCartesian(d3.scaleTime(), d3.scaleLinear())
    .chartLabel('kWh by month (365d)')
    .xDomain(
      fc.extentTime()
        .accessors([d => new Date(d.time)])(monthly_by_load.flat()))
    .yDomain(
      fc.extentLinear()
        .include([0])
        .accessors([d => d.measure])(monthly_by_load.flat()))
    .yLabel('kilowatt-hours')
    .yOrient('left')
    .svgPlotArea(series);

  d3.select('div#monthly')
    .datum(monthly_by_load)
    .call(monthly_chart)
    .select('d3fc-group d3fc-svg.plot-area svg')
    .call(legend);

  d3.select('div#table')
    .selectAll('p')
    .data(monthly_by_load[8])
    .join(
      enter=>enter.append('p')
        .text(d=>new Date(d.time).toLocaleString('default', {month:'long'})
              + ': ' + d.measure.toFixed())
    );
});
