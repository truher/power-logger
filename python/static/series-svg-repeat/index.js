d3.json('/summarydata').then(data => {

  grouped_data = d3.groups(data, d=>d[1])
  grouped_data.sort((a,b)=>d3.ascending(a[0],b[0]));

  group_vals = grouped_data.map(x => x[1]);

  const line = fc
    .seriesSvgLine()
    .crossValue(d => new Date(d[0]/1e6))
    .mainValue(d => d[2]);

  const color = d3.scaleOrdinal(d3.range(group_vals.length),
    d3.schemeCategory10);

  const series = fc.seriesSvgRepeat()
    .orient('horizontal')
    .series(line)
    .decorate(sel => { sel.attr('stroke', (_, i) => color(i)); });

  const flatdata = group_vals.flat();
  const chart = fc.chartCartesian(d3.scaleTime(), d3.scaleLinear())
    .xDomain(fc.extentTime().accessors([d => new Date(d[0]/1e6)])(flatdata))
    .yDomain(fc.extentLinear().accessors([d => {return d[2];}])(flatdata))
    .chartLabel('chart label')
    .xLabel('x label')
    .yLabel('y label')
    .yOrient('left')
    .svgPlotArea(series);

  d3.select('div#foo').datum(group_vals).call(chart);

  const legend = d3.legendColor()
    .shapeWidth(30)
    .orient('vertical')
    .scale(color)
    .labels(grouped_data.map(x => x[0]));

  d3.select('div#foo d3fc-group d3fc-svg svg').call(legend);

});
