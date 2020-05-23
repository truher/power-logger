const container = document.querySelector('#allraw')
d3.select(container).on('draw', () => {
  d3.json('/rawdata').then(json_data => {
    // json_data = [[time,load,kwh,vrms,arms],...]
    grps = d3.groups(json_data, d => d[1])
    // grps = [[load,[[time,load,kwh,vrms,arms],...]],...]
    grpvar = grps.map(x => {
      load = x[0];
      vars = x[1];
      return [
        ['Watts ' + load, vars.map(y=>[new Date(y[0]/1e6),+y[2]])],
        ['Volts rms ' + load, vars.map(y=>[new Date(y[0]/1e6),+y[3]])],
        ['Amps rms ' + load, vars.map(y=>[new Date(y[0]/1e6),+y[4]])] ]
    });
    //grpvar = [[[load,[time,measure]],...],...]
    grpvarflat = grpvar.flat();
    // grpvarflat = [[load,[time,measure]],...]
    grpvarflat.sort((a, b) => (a[0] > b[0]) ? 1 : -1)
    grpvarflatvals = grpvarflat.map(x => x[1])
    d3.select("#allraw")
      .selectAll("div#instance")
      .data(grpvarflatvals)
      .join(
        //enter => enter.append('div').attr('id', 'instance').text('hi'),
        enter => enter.append('div').attr('id', 'instance'),
        update => {
          update.each(function(d, i, g) {
            instance = d3.select(this);
            fc.chartCartesian(d3.scaleTime(), d3.scaleLinear())
              .xDomain(
                fc.extentTime().accessors([d => d[0]])(d))
              .xTicks(10)
              .yDomain(
                fc.extentLinear().accessors([d => d[1]])(d))
              .yTicks(4)
              .yOrient('left')
              .chartLabel(
                grpvarflat[i][0] + ' ' + d3.format(".2f")(d.slice(-1)[0][1]))
              .svgPlotArea(
                fc.seriesSvgLine()
                  .crossValue(d => d[0])
                  .mainValue(d => d[1]))(instance);
            // override the style; css and decoration don't work
            //d3.select('.top-label').style('margin-bottom','0');
          });
      });
  });
});
container.requestRedraw();
// paint the first update immediately
setTimeout(() => {
  container.requestRedraw();
}, 1);

setInterval(() => {
  container.requestRedraw();
}, 1000);

