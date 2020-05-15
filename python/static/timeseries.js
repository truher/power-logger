//const xScale = d3.scaleLinear().domain([-1, 1024]);
//const yScale = d3.scaleLinear().domain([-1, 1024]);

//const series = fc.seriesWebglPoint()
//    //.crossValue(d => d.x)
//    .crossValue((d, i) => i)
//    //.mainValue(d => d.y)  // just Y?
//    .mainValue(d => {return (d.y * d.x);})  // TODO: do this in the server
//    //.xScale(xScale)
//    //.yScale(yScale)
//    .type(d3.symbolCircle)
//    .size(9);

// TODO: do "repeat" for V, I and P
//const multi = fc.seriesWebglMulti()
//    .series([series])
//    //.mapping(function(d,i,s) { console.log("MULTI");console.log(s); return d.value; });
//    .mapping(function(d,i,s) {
//        console.log("MULTI");
//        console.log(d);
//        return d.value; 
//    });

//const chart = fc.chartCartesian(xScale, yScale)
//    //.chartLabel(d => {console.log("LABEL");console.log(d);return d.key;})
//    //.yDomain(fc.extentLinear().accessors([d=>{console.log("Y");console.log(d); return d.x*d.y;}]))
//    .xLabel('x axis')
//    .yLabel('y axis')
//    .yOrient('left') 
//    //.webglPlotArea(multi);
//    .webglPlotArea(series);

//const eee = fc.extentLinear().accessors([d=>{return d.x*d.y;}]);

const container = document.querySelector('#timeseries');

let allloads = {};

//function donothing(selection) {
//    console.log("DONOTHING");
//    selection.each((data, index, group) => {
//        console.log(data);
//        console.log(index);
//        console.log(group);
//    });
//}



d3.select(container)
 //   .on('measure', () => {
 //       xScale.range([0, event.detail.width]);
 //       yScale.range([event.detail.height, 0]);
 //   })
    .on('draw', () => {
        // TODO: do i actually need a separate data source?
        //d3.json('/timeseriesdata').then(function(data) {
        d3.json('/data').then(function(data) {
            //console.log("JSON");
            //console.log(data);
            data.map(function(row){
                zdz = d3.zip(row.x,row.y).map(
                  function(d){
                    return {x:d[0],y:d[1]} // x=V, y=A
                  }
                );
                allloads[row.label] = zdz;
            });
            dd = d3.entries(allloads);
            dd.sort((a,b)=>(a.key > b.key)?1:-1)
            //console.log("DD");
            //console.log(dd);
            d3.select('#timeseries')
                .selectAll('div#instance')
                .data((d,i,n) => {
                    //console.log("DATA0");
                    //console.log(d); // no parent data
                    //console.log("DATA1");
                    //console.log(i);  // always zero
                    //console.log("DATA2");
                    //console.log(n);  // #timeseries
                    //console.log("DATA3");
                    xxx = dd.map(d=>d.value);
                    //console.log(xxx);
                    return xxx;
                    //return dd;
                })
                .join(
                    enter => enter.append('div').attr('id', 'instance'),
                    update => {
                        //console.log("DATA");console.log(update.data());
                        //return update.call(donothing);
                        update.each((d,i,g) => {
                            const series = fc.seriesWebglPoint()
                                //.crossValue(d => d.x)
                                .crossValue((d, i) => i)
                                //.mainValue(d => d.y)  // just Y?
                                .mainValue(d => {return (d.y * d.x);})  // TODO: do this in the server
                                //.xScale(xScale)
                                //.yScale(yScale)
                                .type(d3.symbolCircle)
                                .size(9);
                            //console.log("EACH0");
                            //console.log(d); // data for this instance
                            //console.log("i");
                            //console.log(i); // which instance it is
                            //console.log(dd[i].key); // which instance it is
                            //console.log("EACH2");
                            //console.log(g); // all instances in the selectAll
                            //console.log("EACH3");
                            //gg = d3.select(g[i]);
                            //console.log(gg);
                            xxxx = d3.select(g[i]).data()[0];
                            //xxxxx = xxxx.map(d=>{console.log("HI");console.log(d);});
                            //console.log(xxxx);
                            //console.log(d3.select(g[i]).data()[0].value);
                            //console.log(eee(d3.select(g[i]).data()[0].value));
                            //ddd = eee(xxxx);
                            //console.log(ddd);
                            //x_extent = fc.extentLinear().accessors([(d,i)=>{return i;}])(xxxx)
                            //console.log("x_extent");
                            //console.log(x_extent);
                            //x_min = d3.min(xxxx.map(d=>d.x))
                            //y_min = d3.min(xxxx.map(d=>d.y))
                            //p_min = d3.min(xxxx.map(d=>d.x*d.y))
                            //console.log(x_min + ' ' + y_min + ' ' + p_min);
                            //x_max = d3.max(xxxx.map(d=>d.x))
                            //y_max = d3.max(xxxx.map(d=>d.y))
                            //p_max = d3.max(xxxx.map(d=>d.x*d.y))
                            //i_max = xxxx.length - 1
                            //console.log(x_max + ' ' + y_max + ' ' + p_max);
                            //y_extent = fc.extentLinear().accessors([d=>{return d.x*d.y;}])(xxxx)
                            //console.log("y_extent");
                            //console.log(y_extent);
                            d3.select(g[i]).call(
                                fc.chartCartesian(d3.scaleLinear(), d3.scaleLinear())
                                    //.xDomain([0, i_max])
                                    //.yDomain([p_min, p_max])
                                    .xDomain(fc.extentLinear().accessors([(d,i)=>i])(xxxx))
                                    .yDomain(fc.extentLinear().accessors([d=>d.x*d.y])(xxxx))
                                    //eee(xxxx)
                                    // somehow all charts have the same ydomain now. keeps the last one
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
                            // 
                            //console.log(d3.select(g[i]));
                        });
                        return update;
                        //return update.call(
                        //chart
                        ////.yDomain(fc.extentLinear().accessors([d=>{console.log("hi");console.log(d);return d.x*d.y}])(dd))
                        //)
                    }
                );
        });
    });

container.requestRedraw();

setInterval(() => {container.requestRedraw();}, 500);
