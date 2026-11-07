import {collect} from '../../lib/revenue-collector.js';
export const onRequestPost=context=>collect(context,'okazu');
