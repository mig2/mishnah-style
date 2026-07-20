import { addRoute, initRouter } from './router';
import { DashboardView } from './views/DashboardView';
import { DetectView } from './views/DetectView';
import { ReviewView } from './views/ReviewView';
import { PromoteView, BuildView, RenderView, EnrichView } from './views/PipelineStepView';
import { EntitiesView, EntityDetailView } from './views/EntitiesView';

// Register routes
addRoute(/^$/, () => DashboardView());
addRoute(/^detect$/, () => DetectView());
addRoute(/^review$/, (p) => ReviewView(p));
addRoute(/^review\/(.+)$/, (p) => ReviewView(p));
addRoute(/^promote$/, () => PromoteView());
addRoute(/^build$/, () => BuildView());
addRoute(/^render$/, () => RenderView());
addRoute(/^enrich$/, () => EnrichView());
addRoute(/^entities$/, () => EntitiesView());
addRoute(/^entities\/(\w+)\/(.+)$/, (p) => EntityDetailView(p[0], p[1]));

// Start
const app = document.getElementById('app');
if (app) initRouter(app);
