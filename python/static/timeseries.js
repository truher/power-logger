const container = document.querySelector('#timeseries');

let allloads = {};

d3.select(container).on('draw', () => {
  d3.json('/data').then(function(data) {
    timeout_ms = 0;
    data.map(function(row) {
      if (row.frequency > 0 && row.length > 0) {
        timeout_ms += 1000 * row.length / row.frequency;
      }
      // TODO: compute power in python
      pwr = d3.zip(row.volts, row.amps).map(d=>d[0]*d[1])
      allloads[row.load + ' volts'] = row.volts;
      allloads[row.load + ' amps'] = row.amps;
      allloads[row.load + ' power'] = pwr;
    });
    dd = d3.entries(allloads);
    dd.sort((a, b) => (a.key > b.key) ? 1 : -1)
    vals = dd.map(d => d.value)
    d3.select('#timeseries')
      .selectAll('div#instance')
      //.data((d, i, n) => dd.map(d => d.value))
      .data(vals)
      .join(
        enter => enter.append('div').attr('id', 'instance'),
        update => {
          update.each(function(d, i, g) {
            //const line = fc.seriesWebglLine()
            const line = fc.seriesSvgLine()
              .crossValue((d, i) => i)
              .mainValue(d => d);

            instance = d3.select(this);

            const chart = fc.chartCartesian(d3.scaleLinear(), d3.scaleLinear())
              .xDomain(
                fc.extentLinear()
                  .accessors([(d,i)=>i])(instance.data()[0]))
              .xTicks(10)
              .yDomain(
                fc.extentLinear()
                  .accessors([d=>d])(instance.data()[0]))
              .yTicks(4)
              .chartLabel(dd[i].key)
              .yOrient('left')
              //.webglPlotArea(series);
              .svgPlotArea(line);

            instance.call(chart);
          });
          return update;
        });
    setTimeout(() => {
      container.requestRedraw();
    }, timeout_ms);

  });
});

container.requestRedraw();
