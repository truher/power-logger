//const xScale = d3.scaleLinear().domain([-1, 1024]);
//const yScale = d3.scaleLinear().domain([-1, 1024]);

//const series = fc.seriesWebglPoint()
//    .crossValue(d => d.x)
//    .mainValue(d => d.y)
//    .xScale(xScale)
//    .yScale(yScale)
//    .type(d3.symbolCircle)
//    .size(9);

//const multi = fc.seriesWebglMulti()
//    .series([series])
//    .mapping(function(d,i,s) { return d.value; });

//const chart = fc.chartCartesian(d3.scaleLinear(), d3.scaleLinear())
//    .xDomain(fc.extentLinear().accessors([d=>{console.log(d);return d;}]))
//    .webglPlotArea(multi)
//    .chartLabel(d => d.key)
//    .xLabel('x axis')
//    .yLabel('y axis')
//    .yOrient('left') ;

const container = document.querySelector('#small-multiples');

let allloads = {};

d3.select(container)
//    .on('measure', () => {
//        xScale.range([0, event.detail.width]);
//        yScale.range([event.detail.height, 0]);
//    })
    .on('draw', () => {
        d3.json('/data').then(function(data) {
            data.map(function(row){
                zdz = d3.zip(row.x,row.y).map(function(d){return {x:d[0],y:d[1]}});
                allloads[row.label] = zdz;
            });
            dd = d3.entries(allloads);
            dd.sort((a,b)=>(a.key > b.key)?1:-1)
            d3.select('#small-multiples')
                .selectAll('div#instance')
                .data((d,i,n) => {
                    xxx = dd.map(d=>d.value);
                    return xxx;
                })  //dd)
                .join(
                    enter => enter.append('div').attr('id', 'instance'),
                    update => {
                        //update.call(chart)
                        update.each((d,i,g) => {
                            const series = fc.seriesWebglPoint()
                                .crossValue(d => d.x)
                                .mainValue(d => d.y)
                                .type(d3.symbolCircle)
                                .size(9);
                            xxxx = d3.select(g[i]).data()[0];
                            // should use "this" below?
                            d3.select(g[i]).call(
                                fc.chartCartesian(d3.scaleLinear(), d3.scaleLinear())
                                    .xDomain(fc.extentLinear().accessors([d=>d.x])(xxxx))
                                    .yDomain(fc.extentLinear().accessors([d=>d.y])(xxxx))
                                    .chartLabel(dd[i].key)
                                    .xLabel('x axis')
                                    .yLabel('y axis')
                                    .yOrient('left') 
                                    .webglPlotArea(series)
                                    //.webglPlotArea(series)(d3.select(g[i]));
                                //chart
                                //.yDomain(eee(xxxx))
                                //.chartLabel(dd[i].key)
                            );

                        });
                        return update;
                    }
                );
        });
    });

container.requestRedraw();

setInterval(() => {container.requestRedraw();}, 500);
