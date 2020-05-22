d3.json('/rawdata').then(json_data => {
  // json_data = [[time,load,kwh,vrms,arms],...]
  // group by load
  grps = d3.groups(json_data, d => d[1])
  // grps = [[load,[[time,load,kwh,vrms,arms],...]],...]
  grpvar = grps.map(x => {
    load = x[0];
    vars = x[1];
    return [
      ['kWh ' +load, vars.map(y=>[new Date(y[0]/1e6),+y[2]])],
      ['Vrms ' + load, vars.map(y=>[new Date(y[0]/1e6),+y[3]])],
      ['Arms ' + load, vars.map(y=>[new Date(y[0]/1e6),+y[4]])] ]
  });
  //grpvar = [[[load,[time,measure]],...],...]
  grpvarflat = grpvar.flat();
  // grpvarflat = [[load,[time,measure]],...]
  grpvarflat.sort((a, b) => (a[0] > b[0]) ? 1 : -1)
  grpvarflatvals = grpvarflat.map(x => x[1])

  instances = d3.select("#allraw")
    .selectAll("div#instance")
    .data(grpvarflatvals)
    .enter()
      .append('div').attr('id', 'instance');

  instances.each(function(d, i, g) {
    instance = d3.select(this);

    const lline = fc.seriesSvgLine()
      .crossValue(d => d[0])
      .mainValue(d => d[1]);

    const cchart = fc.chartCartesian(d3.scaleTime(), d3.scaleLinear())
      .xDomain(fc.extentTime().accessors([d => d[0]])(instance.data()[0]))
      .xTicks(10)
      .yDomain(fc.extentLinear().accessors([d => d[1]])(instance.data()[0]))
      .yTicks(4)
      .yOrient('left')
      .chartLabel(grpvarflat[i][0])
      .svgPlotArea(lline);

    instance.call(cchart);

  });
});
