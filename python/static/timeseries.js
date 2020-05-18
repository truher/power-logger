const container = document.querySelector('#timeseries');

let allloads = {};

d3.select(container).on('draw', () => {
  d3.json('/data').then(function(data) {
    data.map(function(row) {
      zdz = d3.zip(row.x, row.y).map(
        function(d) {
          return {
            x: d[0],
            y: d[1]
          } // x=V, y=A
        });
      allloads[row.label] = zdz;
    });
    dd = d3.entries(allloads);
    dd.sort((a, b) => (a.key > b.key) ? 1 : -1)
    d3.select('#timeseries')
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
              .crossValue((d, i) => i)
              .mainValue(d => {
                return (d.y * d.x);
              }) // TODO: do this in the server
              .type(d3.symbolCircle)
              .size(4);
            instance = d3.select(this);
            fc.chartCartesian(d3.scaleLinear(), d3.scaleLinear())
              .xDomain(
                fc.extentLinear()
                  .accessors([(d, i) => i])(instance.data()[0]))
              .yDomain(
                fc.extentLinear()
                  .include([0])
                  .accessors([d => d.x * d.y])(instance.data()[0]))
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

