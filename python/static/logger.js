const container = document.querySelector('#small-multiples');

let allloads = {};

d3.select(container).on('draw', () => {
console.log("draw");
  d3.json('/data').then(function(data) {
    timeout_ms = 0;
    data.map(function(row) {
      if (row.frequency > 0 && row.length > 0) {
        timeout_ms += 1000 * row.length / row.frequency;
      }
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
                  .pad([0.05,0.05])
                  .padUnit('percent')
                  .symmetricalAbout(0)
                  .include([-1,1]) // volts
                  .accessors([d => d.volts])(instance.data()[0]))
              .yDomain(
                fc.extentLinear()
                  .pad([0.05,0.05])
                  .padUnit('percent')
                  .symmetricalAbout(0)
                  .include([-1,1]) // amps
                  .accessors([d => d.amps])(instance.data()[0]))
              .chartLabel(dd[i].key)
              .xLabel('x axis')
              .yLabel('y axis')
              .yOrient('left')
              .webglPlotArea(series)(instance);
          });
          return update;
        });
    setTimeout(() => {
      container.requestRedraw();
    }, timeout_ms);
  });
});

container.requestRedraw();
