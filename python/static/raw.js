d3.json('/rawdata').then(json_data => {

  const hourly_records = json_data.map(x=>{
    return {
      time:x[0]/1e6,
      load:x[1],
      measure:+x[2]
    };
  });

  const WINDOW_SIZE = 5000;
  const hourly_window = hourly_records.slice(-1 * WINDOW_SIZE);
  const load_groups_hourly_records = d3.groups(hourly_window, d=>d.load)
  load_groups_hourly_records.sort((a,b)=>d3.ascending(a[0],b[0]));

  const hourly_by_load = load_groups_hourly_records.map(x => x[1]);

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
    .chartLabel('kWh raw observations (' + WINDOW_SIZE + ')')
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

  d3.select('div#raw')
    .datum(hourly_by_load)
    .call(hourly_chart)
    .select('d3fc-group d3fc-svg.plot-area svg')
    .call(legend);
});
