const xScale = d3.scaleLinear().domain([-1, 1024]);
const yScale = d3.scaleLinear().domain([-1, 1024]);

const series = fc.seriesWebglPoint()
    .crossValue(d => d.x)
    .mainValue(d => d.y)
    .xScale(xScale)
    .yScale(yScale)
    .type(d3.symbolCircle)
    .size(16)
    .defined(() => true)
    .equals(() => false)
    .decorate(program => {
        fc.webglFillColor([0.0,0.75,0.375,1.0])(program);
        const gl = program.context();
        gl.enable(gl.BLEND);
        gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE,
          gl.ONE_MINUS_SRC_ALPHA);
    });

var multi = fc.seriesWebglMulti()
    .series([series])
    .mapping(function(d,i,s) { return d.values; });

var gridlines = fc.annotationSvgGridline()

const chart = fc.chartCartesian(xScale, yScale)
    .webglPlotArea(multi)
    .chartLabel(d => d.label)
    .xLabel('x axis')
    .yLabel('y axis')
    .svgPlotArea(gridlines)
    .yOrient('left') ;

const container = document.querySelector('#small-multiples');

d3.select(container)
    .on('measure', () => {
        xScale.range([0, event.detail.width]);
        yScale.range([event.detail.height, 0]);
    })
    .on('draw', () => {
        d3.json('/data').then(function(data) {
            zipped = data.map(function(x){
                zdz = d3.zip(x.x,x.y).map(function(d){return {x:d[0],y:d[1]}});
                return {label: x.label, values:zdz}
            });

            d3.select('#small-multiples')
                .selectAll('div#instance')
                .data(zipped)
                .join(
                    enter => enter.append('div').attr('id', 'instance'),
                    update => update.call(chart)
                );
        });
    });

container.requestRedraw();

setInterval(() => {container.requestRedraw();}, 1000); // 15 fps
