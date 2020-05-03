const xScale = d3.scaleLinear().domain([-1, 1024]);
const yScale = d3.scaleLinear().domain([-1, 1024]);
const container = document.querySelector('d3fc-canvas');

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

d3.select(container)
    .on('measure', () => {
        xScale.range([0, event.detail.width]);
        yScale.range([event.detail.height, 0]);
        series.context(container.querySelector('canvas').getContext('webgl'));
    })
    .on('draw', () => {
        d3.text('/data').then(function(text) {
            var data = d3.tsvParseRows(text, function(d) {
                return {x:+d[0],y:+d[1]};
            });
            series(data);
        });
    });

container.requestRedraw();

setInterval(() => {container.requestRedraw();}, 67); // 15 fps
