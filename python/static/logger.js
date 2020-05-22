const container = document.querySelector('#small-multiples');

let allloads = {};

d3.select(container).on('draw', () => {
  d3.json('/data').then(function(data) {
    data.map(function(row) {
      zdz = d3.zip(row.volts, row.amps).map(function(d) {
        return {
          volts: d[0],
          amps: d[1]
        }
      });
      allloads[row.load] = zdz;
    });
    dd = d3.entries(allloads);
    dd.sort((a, b) => (a.key > b.key) ? 1 : -1)
    d3.select('#small-multiples')
      .selectAll('div#instance')
      .data((d, i, n) => {
        xxx = dd.map(d => d.value);
        return xxx;
      })
      .join(
        enter => enter.append('div').attr('id', 'instance'),
        update => {
          update.each(function(d, i, g) {
            const series = fc.seriesWebglPoint()
              .crossValue(d => d.volts)
              .mainValue(d => d.amps)
              .type(d3.symbolCircle)
              .size(1)
              .decorate(program => {
                fc.webglFillColor()
                  .value([0,0,1,1])(program);
              });
            instance = d3.select(this);
            fc.chartCartesian(d3.scaleLinear(), d3.scaleLinear())
              .xDomain(
                fc.extentLinear()
                  .include([-200,200]) // volts
                  .accessors([d => d.volts])(instance.data()[0]))
              .yDomain(
                fc.extentLinear()
                  .include([-100,100]) // amps
                  .accessors([d => d.amps])(instance.data()[0]))
              .chartLabel(dd[i].key)
              .xLabel('x axis')
              .yLabel('y axis')
              .yOrient('left')
              .webglPlotArea(series)(instance);
          });
          return update;
        });
  });
});

container.requestRedraw();

setInterval(() => {
  container.requestRedraw();
}, 500);

