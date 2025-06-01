const universalPredictionsRouter = require('./routes/universal-predictions');
const brandEngagementRouter = require('./routes/brand-engagement');
const annotationModelsRouter = require('./routes/annotation-models');

// Routes
app.use('/api/universal', universalPredictionsRouter);
app.use('/api/brand', brandEngagementRouter);
app.use('/api/annotations', annotationModelsRouter); 