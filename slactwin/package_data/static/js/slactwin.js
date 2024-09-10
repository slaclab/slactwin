'use strict';

SIREPO.app.config(function() {
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.lattice = {
        elementColor: {
        },
        elementPic: {
            drift: ['DRIFT', 'EMFIELD_CARTESIAN', 'EMFIELD_CYLINDRICAL', 'WAKEFIELD'],
            lens: ['ROTATIONALLY_SYMMETRIC_TO_3D'],
            magnet: ['QUADRUPOLE', 'DIPOLE'],
            solenoid: ['SOLENOID', 'SOLRF'],
            watch: ['WRITE_BEAM', 'WRITE_SLICE_INFO'],
            zeroLength: [
                'CHANGE_TIMESTEP',
                'OFFSET_BEAM',
                'SPACECHARGE',
                'STOP',
            ],
        },
    };
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="SearchTerms">
          <div data-search-terms="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="ColumnList" data-ng-class="fieldClass">
          <div data-column-list="" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="parameterWithExternalLattice" data-parameter-with-lattice="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}" data-path-to-models="externalLattice"></div>
    `;
});

SIREPO.app.factory('slactwinService', function(appState, frameCache, persistentSimulation, $location, $rootScope) {
    const self = {};
    self.computeModel = analysisModel => 'animation';
    self.selectSearchFieldText = 'Select Search Field';

    self.elementForName = (name) => {
        for (const el of self.latticeModels().elements) {
            if (el.name === name) {
                return el;
            }
        }
        return null;
    };

    self.getArchiveId = () => {
        return $location.search().archiveId;
    };

    self.loadArchive = () => {
        const names = [];
        const archiveId = self.getArchiveId();
        for (const m in appState.models) {
            if (appState.models[m] && 'archiveId' in appState.models[m]) {
                appState.models[m].archiveId = archiveId;
                names.push(m);
            }
        }
        appState.saveChanges(names, () => {
            frameCache.getFrame('summaryAnimation', 0, false, (index, data) => {
                if (data.error) {
                    return;
                }
                frameCache.setFrameCount(1);
                self.summary = data.summary;
                self.particles = data.particles;
                appState.models.externalLattice = data.lattice;
                $rootScope.$broadcast('sr-archive-loaded');
            });
        });
    };

    self.setArchiveId = (archiveId) => {
        $location.search('archiveId', archiveId);
    };

    self.initController = (controller, $scope) => {
        let firstCheck = true;
        $scope.loadingMessage = "Reading archive";

        const init = () => {
            controller.simScope = $scope;
            controller.simComputeModel = 'animation';
            controller.simState = persistentSimulation.initSimulationState(controller);
        };

        controller.simHandleStatus = (data) => {
            if (data.state === 'completed') {
                self.loadArchive();
                return;
            }
            if (firstCheck) {
                firstCheck = false;
                if (data.state == 'missing' || data.state == 'error') {
                    controller.simState.runSimulation();
                }
            }
        };

        init();
    };

    self.latticeModels = () => {
        return appState.models.externalLattice.models;
    };

    self.selectElementId = (id) => {
        self.latticeModels().beamlines[0].items.forEach((v, idx) => {
            if (id === v) {
                $rootScope.$broadcast('sr-beamlineItemSelected', idx);
            }
        });
    };

    appState.setAppService(self);

    return self;
});

SIREPO.app.controller('VizController', function(appState, frameCache, panelState, slactwinService, $scope) {
    const self = this;

    slactwinService.initController(self, $scope);

    $scope.$on('sr-archive-loaded', () => {
        $scope.loadingMessage = "";
        self.outputFiles = [];
        slactwinService.particles.forEach((info) => {
            var outputFile = {
                info: info,
                reportType: 'heatmap',
                viewName: 'elementAnimation',
                modelAccess: {
                    modelKey: info.modelKey,
                    getData: () => {
                        return appState.models[info.modelKey];
                    },
                },
                panelTitle: info.name.replace('_', ' '),
            };
            self.outputFiles.push(outputFile);
            panelState.setError(info.modelKey, null);
            if (! appState.models[info.modelKey]) {
                appState.models[info.modelKey] = {};
            }
            var m = appState.models[info.modelKey];
            m.archiveId = slactwinService.getArchiveId();
            m.plotName = info.name;
            appState.setModelDefaults(m, 'elementAnimation');
            appState.saveQuietly(info.modelKey);
            frameCache.setFrameCount(1, info.modelKey);
        });
    });
});

SIREPO.app.controller('InitController', function(appState, requestSender, slactwinService) {
    const self = this;
    const init = () => {
        slactwinService.setArchiveId(null);
        appState.clearModels();
        appState.listSimulations((resp) => {
            requestSender.localRedirect('search-results', {
                ':simulationId': resp[0].simulationId,
            });
        });
    }

    init();
});

SIREPO.app.controller('SearchController', function(appState) {
    const self = this;
    self.appState = appState;
});

SIREPO.app.controller('BeamController', function() {
    const self = this;
});

SIREPO.app.controller('LatticeController', function(slactwinService, $scope) {
    const self = this;
    slactwinService.initController(self, $scope);

    $scope.$on('sr-archive-loaded', () => {
        $scope.loadingMessage = "";
        self.hasLattice = true;
    });
});

SIREPO.app.directive('appFooter', function(slactwinService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(authState, panelState, slactwinService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <ul class="nav navbar-nav" data-ng-if=":: authState.isLoggedIn">
              <li class="sim-section" data-ng-class="{active: nav.isActive('search') || nav.isActive('search-results') }"><a href data-ng-click="nav.openSection('search')"><span class="glyphicon glyphicon-search"></span> Search</a></li>
            </ul>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded data-ng-if="hasQuery()">
                <div data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive('beam')}"><a href data-ng-click="nav.openSection('beam')"><span class="glyphicon glyphicon-flash"></span> Beam</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('lattice')}"><a href data-ng-click="nav.openSection('lattice')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>

                  <li class="sim-section" data-ng-class="{active: nav.isActive('vizualization')}"><a href data-ng-click="nav.openSection('viz')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function($element, $scope) {
            $scope.authState = authState;

            $scope.hasQuery = slactwinService.getArchiveId;

            panelState.waitForUI(() => {
                $($element).find("li[data-settings-menu='nav']").hide();
            });
        },
    };
});

SIREPO.app.directive('latticeFooter', function(panelState, slactwinService) {
    return {
        restrict: 'A',
        scope: {
            width: '@',
            modelName: '@',
        },
        template: ``,
        controller: function($scope) {

            function detectOverlap(positions, pos) {
                for (let p of positions) {
                    if (rectanglesOverlap(pos, p)) {
                        return p;
                    }
                }
            }

            function labelElements() {
                $('.sr-lattice-label').remove();
                const parentRect = $('#sr-lattice')[0].getBoundingClientRect();
                const positions = [];
                const labeled = [];
                $("[class^='sr-beamline']").each( (_ , element) => {
                    positions.push(element.getBoundingClientRect());
                });
                $('#sr-lattice').find('title').each((v, node) => {
                    const values = $(node).text().split(': ');
                    if (values[1].indexOf('CHANGE_TIMESTEP') >= 0) {
                        return;
                    }
                    const isMonitorOrInstrument = values[1].indexOf('WRITE_BEAM') >= 0;
                    const rect = node.parentElement.getBoundingClientRect();
                    let pos = [
                        rect.left - parentRect.left,
                        isMonitorOrInstrument
                            ? rect.top - parentRect.top - 25
                            : rect.bottom - parentRect.top + 10,

                    ];
                    const el = slactwinService.elementForName(values[0]);
                    let div = $('<div/>', {
                        class: 'sr-lattice-label badge' + (el ? (' sr-lattice-label-' + el._id) : ''),
                    })
                        .html(values[0])
                        .css({
                            left: pos[0],
                            top: pos[1],
                            position: 'absolute',
                            cursor: 'pointer',
                            'user-select': 'none',
                        })
                        .on('click', () => {
                            $scope.elementClicked(values[0]);
                            $scope.$applyAsync();
                        })
                        .on('dblclick', () => {
                            $scope.elementClicked(values[0], true);
                            $scope.$applyAsync();
                        })
                        .appendTo($('.sr-lattice-holder'));
                    const maxChecks = 8;
                    let checkCount = 1;
                    let p = detectOverlap(positions, div[0].getBoundingClientRect());
                    let yOffset = 0;
                    const c = 3;
                    while (p) {
                        if (isMonitorOrInstrument) {
                            const d = div[0].getBoundingClientRect().bottom - p.top - 1;
                            if (d > c) {
                                yOffset -= d;
                            }
                            yOffset -= c;
                        }
                        else {
                            const d = p.bottom - div[0].getBoundingClientRect().top + 1;
                            if (d > c) {
                                yOffset += d;
                            }
                            yOffset += c;
                        }
                        div.css({
                            top: pos[1] + yOffset,
                        });
                        p = detectOverlap(positions, div[0].getBoundingClientRect());
                        if (checkCount++ > maxChecks) {
                            break;
                        }
                    }
                    positions.push(div[0].getBoundingClientRect());
                });
            }

            function rectanglesOverlap(pos1, pos2) {
                if (pos1.left > pos2.right || pos2.left > pos1.right) {
                    return false;
                }
                if (pos1.top > pos2.bottom || pos2.top > pos1.bottom) {
                    return false;
                }
                return true;
            }

            function setSelectedId(elId) {
                if ($scope.selectedId != elId) {
                    if ($scope.selectedId) {
                        const node = $('.sr-lattice-label-' + $scope.selectedId);
                        node.removeClass('sr-selected-badge');
                    }
                    $scope.selectedId = elId;
                    const node = $('.sr-lattice-label-' + $scope.selectedId);
                    node.addClass('sr-selected-badge');
                }
            }

            $scope.elementClicked = (name, showEditor) => {
                const el = slactwinService.elementForName(name);
                if (el) {
                    //setSelectedId(el._id);
                    slactwinService.selectElementId(el._id);
                }
            };

            $scope.destroy = () => $('.sr-lattice-label').off();

            $scope.$on('sr-beamlineItemSelected', (e, idx) => {
                setSelectedId(slactwinService.latticeModels().beamlines[0].items[idx]);
            });

            $scope.$on('sr-renderBeamline', () => {
                panelState.waitForUI(labelElements);
            });
        },
    };
});

SIREPO.app.directive('pvTable', function(appState, slactwinService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <table class="table table-hover table-condensed">
              <thead><tr>
                <th data-ng-repeat="col in columns track by $index">
                  {{ col[0] }}
                </th>
              </tr></thead>
              <tbody>
                <tr style="cursor: pointer" data-ng-click="selectRow(row)" data-ng-class="{active: isActive(row)}" data-ng-repeat="row in rows track by $index">
                  <td>{{ dataframe.Variable[row.index] }}</td>
                  <td>{{ dataframe.device_pv_name[row.index] }}</td>
                  <td class="text-right">{{ format(row.index, 'pv_value') }}
                    <div class="text-left st-units">({{ dataframe.pv_unit[row.index] }})</div></td>
                  <td>{{ dataframe.impact_name[row.index] }}</td>
                  <td class="text-right">{{ format(row.index, 'impact_value') }}
                    <div class="text-left st-units">({{ dataframe.impact_unit[row.index] }})</div></td>
                  <td class="text-right">{{ format(row.index, 'impact_offset', true) }}</td>
                  <td class="text-right">{{ format(row.index, 'impact_factor', true) }}</td>
                </tr>
              </tbody>
            <table>
        `,
        controller: function($scope) {
            $scope.columns = [
                ['Variable', 'Variable'],
                ['PV Name', 'device_pv_name'],
                ['PV Value', 'pv_value', 'pv_unit'],
                ['IMPACT-T Name', 'impact_name'],
                ['IMPACT-T Value', 'impact_value', 'impact_unit'],
                ['IMPACT-T Offset', 'impact_offset'],
                ['IMPACT-T Factor', 'impact_factor'],
            ];

            const init = () => {
                $scope.dataframe = slactwinService.summary.pv_mapping_dataframe;
                $scope.rows = [];
                const ids = slactwinService.latticeModels().beamlines[0].items;
                Object.keys($scope.dataframe.impact_name).forEach((k, idx) => {
                    const name = $scope.dataframe.impact_name[k].split(':')[0];
                    const el = slactwinService.elementForName(name);
                    if (el && ids.includes(el._id)) {
                        $scope.rows.push({
                            el: el,
                            index: idx,
                        });
                    }
                });
            };

            $scope.format = (index, name, notZero) => {
                const v = $scope.dataframe[name][index];
                if (notZero && v === 0) {
                    return '';
                }
                return appState.formatFloat(v, 6);
            };

            $scope.isActive = (row) => {
                return row.el._id === $scope.selectedId;
            };

            $scope.selectRow = (row) => {
                slactwinService.selectElementId(row.el._id);
            };

            $scope.$on('sr-beamlineItemSelected', (e, idx) => {
                $scope.selectedId = slactwinService.latticeModels().beamlines[0].items[idx];
            });

            init();

            $scope.slactwinService = slactwinService;
            $scope.$on('sr-archive-loaded', init);
        },
    };
});

SIREPO.app.directive('archiveNavigation', function(appState, requestSender, slactwinService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="text-right" data-ng-if="archiveIds">
              <div style="margin: 0 1em 1em 0">
                <button type="button" class="btn btn-default" data-ng-click="next(0)" data-ng-disabled="! archiveIds[0]">
                  <span class="glyphicon glyphicon-triangle-left"> </span></button>
                <button type="button" class="btn btn-default" data-ng-click="next(1)" data-ng-disabled="! archiveIds[1]">
                  <span class="glyphicon glyphicon-triangle-right"> </span></button>
              </div>
            </div>
        `,
        controller: function($scope) {

            const init = () => {
                requestSender.sendStatefulCompute(
                    appState,
                    (resp) => {
                        if (resp.error) {
                            //TODO(pjm): display error message
                        }
                        $scope.archiveIds = resp.archiveIds;
                    },
                    {
                        method: 'next_and_previous_archives',
                        args: {
                            archiveId: slactwinService.getArchiveId(),
                        },
                    },
                );
            };

            $scope.next = (direction) => {
                if ($scope.archiveIds[direction]) {
                    slactwinService.setArchiveId($scope.archiveIds[direction]);
                    slactwinService.loadArchive();
                    init();
                }
            };

            init();
        },
    };
});

SIREPO.app.directive('loadingIndicator', function($timeout) {
    return {
        restrict: 'A',
        scope: {
            message: '<loadingIndicator',
        },
        template: `
            <div style="margin-left: 2em; margin-top: 1ex;" class="lead" data-ng-show="message && ready"><img src="/static/img/sirepo_animated.gif" /> {{ message }}</div>
        `,
        controller: function($scope) {
            $timeout(() => $scope.ready = true, 500);
        },
    };
});

SIREPO.app.directive('archiveSummary', function(appState, slactwinService) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div style="margin-bottom: 1em">{{ summary.description }}</div>

            <div>{{ summary.inputs['distgen:n_particle'] | number }} macroparticles</div>
            <div>{{ summary.Nbunch }} bunch{{ summary.Nbunch > 1 ? 'es' : '' }} of {{ models.beam.particle }}s</div>
            <div>Total charge: {{ summary.inputs['distgen:total_charge:value'] | number:1 }} pC</div>
            <div>Processor domain: {{ summary.Nprow }} x {{ summary.Npcol }} = {{ summary.Nprow * summary.Npcol }} CPUs</div>
            <div>Space charge grid: {{ models.simulationSettings.Nx }} x {{ models.simulationSettings.Ny }} x {{ models.simulationSettings.Nz }}</div>
            <div data-ng-if="timestep">Timestep: {{ models.simulationSettings.Dt * 1e12 | number:1 }} ps to {{ timestep.pos }} m, then {{ timestep.dt * 1e12 | number:1 }} ps until the end
            <div>Final emittance(x, y): {{ summary.outputs.end_norm_emit_x * 1e6 | number:3 }}, {{ summary.outputs.end_norm_emit_y * 1e6 | number:3 }} µm</div>
            <div>Final bunch length: {{ summary.outputs.end_sigma_z * 1e3 | number:2 }} mm</div>

            <div style="margin-top: 1em">Run time: {{ summary.run_time / 60 | number:1 }} minutes</div>
        `,
        controller: function($scope) {
            const init = () => {
                $scope.summary = slactwinService.summary;
                $scope.models = slactwinService.latticeModels();
                let cts = {};
                for (const el of $scope.models.elements) {
                    if (el.type === 'CHANGE_TIMESTEP') {
                        cts[el._id] = el;
                    }
                }
                $scope.models.beamlines[0].items.some((id, i) => {
                    if (cts[id]) {
                        $scope.timestep = cts[id];
                        $scope.timestep.pos = $scope.models.beamlines[0].positions[i].elemedge;
                        return true;
                    }
                });
            };

            init();
            $scope.$on('sr-archive-loaded', init);
        },
    };
});

SIREPO.app.directive('searchForm', function(appState, requestSender, slactwinService) {
    return {
        restrict: 'A',
        scope: {
            model: '=searchForm',
        },
        template: `
            <div class="col-md-8 col-md-offset-1">
              <div data-advanced-editor-pane="" data-view-name="'searchSettings'" data-field-def="basic" data-want-buttons="true"></div>
              <div data-loading-indicator="loadingMessage"></div>
            </div>
            <div class="col-sm-12">
              <div data-search-results="searchResults" data-model="model"></div>
            </div>
        `,
        controller: function(slactwinService, $scope) {

            const extractNames = (resp, columns) => {
                if (angular.isObject(resp)) {
                    for (const k in resp) {
                        if (k === 'names') {
                            for (const v of resp[k]) {
                                columns.push(v);
                            }
                        }
                        else {
                            extractNames(resp[k], columns);
                        }
                    }
                }
                return columns;
            };

            const getColumns = () => {
                requestSender.sendStatefulCompute(
                    appState,
                    (resp) => {
                        $scope.model.columns = extractNames(resp, []);
                        getSearchResults();
                    },
                    {
                        method: 'get_columns',
                    },
                );
            };

            const getSearchResults = () => {
                requestSender.sendStatefulCompute(
                    appState,
                    (resp) => {
                        $scope.loadingMessage = "";
                        if (resp.error) {
                            //TODO(pjm): display error message
                        }
                        $scope.searchResults = resp.searchResults;
                    },
                    {
                        method: 'search_archives',
                    },
                );
            };

            const init = () => {
                $scope.loadingMessage = "Loading archives";
                getColumns();
            };

            init();
        },
    };
});

SIREPO.app.directive('searchResults', function(appState, requestSender, slactwinService) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            searchResults: '=',
        },
        template: `
             <div data-search-results-table="" data-model="model"></div>
             <div class="col-sm-12" style="max-height: calc(100vh - 100px); overflow-y: visible">
               <div data-ng-repeat="row in searchResults" style="padding: 1ex">
                 <a href data-ng-click="openArchive(row)">Archive {{ row.description }}</a>
               </div>
             </div>
        `,
        controller: function(requestSender, slactwinService, $scope) {
            $scope.openArchive = (row) => {
                requestSender.localRedirect(SIREPO.APP_SCHEMA.appModes.default.localRoute, {
                    ':simulationId': appState.models.simulation.simulationId,
                });
                slactwinService.setArchiveId(row.archiveId);
            };
        },
    };
});

SIREPO.app.directive('searchTerms', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div data-ng-if="showTerms()" class="st-search-terms col-sm-12">
              <div class="row">
                <div class="text-center col-sm-3 col-sm-offset-5"><label>Minimum</label></div>
                <div class="text-center col-sm-3"><label>Maximum</label></div>
              </div>
              <div class="form-group"
                data-ng-repeat="searchTerm in model.searchTerms track by $index"
                data-ng-show="showRow($index)">
                <div class="col-sm-2"></div>
                <div data-field-editor="'column'" data-label-size="0"
                   data-field-size="3" data-model-name="'searchTerm'"
                   data-model="searchTerm"></div>
                 <div data-field-editor="'minValue'" data-label-size="0"
                   data-field-size="3" data-model-name="'searchTerm'"
                   data-model="searchTerm"></div>
                 <div data-field-editor="'maxValue'" data-label-size="0"
                   data-field-size="3" data-model-name="'searchTerm'"
                   data-model="searchTerm"></div>
                 <div class="col-sm-1" style="margin-top: 5px; margin-left: -15px"
                   data-ng-show="! isEmpty($index)">
                   <button class="btn btn-info btn-xs" type="button"
                     data-ng-click="deleteRow($index)">
                     <span class="glyphicon glyphicon-remove"></span>
                   </button>
                 </div>
               </div>
            </div>`,
        controller: function(appState, slactwinService, $scope) {
            const maxSearchTerms = 10;
            let isInitialized = false;

            function updateTerms() {
                for (let i = 0; i < maxSearchTerms; i++) {
                    if (! $scope.model.searchTerms[i]) {
                        $scope.model.searchTerms[i] = {
                            column: slactwinService.selectSearchFieldText,
                            minValue: '',
                            maxValue: '',
                        };
                    }
                }
            }

            $scope.deleteRow = idx => {
                $scope.model.searchTerms.splice(idx, 1);
                updateTerms();
            };

            $scope.isEmpty = idx => {
                const search = $scope.model.searchTerms[idx];
                return (
                    search.column != slactwinService.selectSearchFieldText
                    || search.term
                ) ? false : true;
            };

            $scope.showRow = idx => (idx == 0) || ! $scope.isEmpty(idx - 1);

            $scope.showTerms = () => {
                if (! $scope.model.columns) {
                    return false;
                }
                if (! isInitialized) {
                    isInitialized = true;
                    updateTerms();
                }
                return true;
            };
        },
    };
});

SIREPO.app.directive('columnList', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select data-ng-if="appState.models.searchSettings.columns"
              class="form-control pull-right" style="width: auto"
              data-ng-model="model[field]"
              data-ng-options="item as item for item in columns">
            </select>
        `,
        controller: function(appState, slactwinService, $scope) {
            const updateColumns = () => {
                $scope.columns = appState.clone(appState.models.searchSettings.columns);
                $scope.columns.unshift(slactwinService.selectSearchFieldText);
            };
            updateColumns();
            $scope.appState = appState;
            $scope.$watchCollection('appState.models.searchSettings.columns', updateColumns);
        },
    };
});

SIREPO.app.directive('columnPicker', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
        },
        template: `
            <div class="form-group form-group-sm pull-right" style="margin: 0; font-weight: 700">
              <select class="form-control" data-ng-model="selected" ng-change="selectColumn()">
                <option ng-repeat="column in availableColumns">{{column}}</option>
              </select>
            </div>
        `,
        controller: function(appState, $scope) {
            $scope.selected = null;
            const addColumnText = 'Add Column';

            function setAvailableColumns() {
                $scope.availableColumns = $scope.model.columns.filter(value => {
                    return ! $scope.model.selectedColumns.includes(value);
                });
                $scope.availableColumns.unshift(addColumnText);
                $scope.selected = addColumnText;
            }

            $scope.selectColumn = () => {
                if ($scope.selected === null) {
                    return;
                }
                $scope.model.selectedColumns.push($scope.selected);
            };

            $scope.$watchCollection('model.columns', setAvailableColumns);
            $scope.$watchCollection('model.selectedColumns', setAvailableColumns);
        },
    };
});

SIREPO.app.directive('searchResultsTable', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
        },
        template: `
            <div>
              <div>
                <div data-column-picker="" data-model="model"></div>
                <table class="table table-striped table-hover">
                  <thead>
                    <tr>
                      <th data-ng-repeat="column in columnHeaders track by $index" class="st-removable-column" style="width: 100px; height: 40px; white-space: nowrap">
                        <span data-ng-class="arrowClass(column)"></span>
                        <span style="cursor: pointer" data-ng-click="sortCol(column)">{{ column }}</span>
                        <button type="submit" class="btn btn-info btn-xs st-remove-column-button" data-ng-if="showDeleteButton($index)" data-ng-click="deleteCol(column)"><span class="glyphicon glyphicon-remove"></span></button>
                      </th>
                      <th></th>
                    </tr>
                  </thead>
                </table>
              </div>
            </div>
        `,
        controller: function(appState, $scope) {

            const updateColumns = () => {
                if (! $scope.model.selectedColumns) {
                    $scope.model.selectedColumns = ['snapshot_end'];
                }
                $scope.columnHeaders = [];
                for (const c of $scope.model.selectedColumns) {
                    $scope.columnHeaders.push(c);
                }
            };

            $scope.arrowClass = (column) => {
                if ($scope.model.sortColumn && (column == $scope.model.sortColumn[0])) {
                    const dir = $scope.model.sortColumn[1 ] ? 'up' : 'down';
                    return {
                        glyphicon: true,
                        [`glyphicon-arrow-${dir}`]: true,
                    };
                }
                return {};
            };

            $scope.deleteCol = (column) => {
                $scope.model.selectedColumns.splice(
                    $scope.model.selectedColumns.indexOf(column),
                    1
                );
            };

            $scope.showDeleteButton = (index) => {
                return index > 0;
            };

            $scope.sortCol = (column) => {
                if ($scope.model.sortColumn && $scope.model.sortColumn[0] == column) {
                    $scope.model.sortColumn[1] = ! $scope.model.sortColumn[1];
                }
                else {
                    $scope.model.sortColumn = [column, true];
                }
            };

            $scope.$watchCollection('model.selectedColumns', updateColumns);
        },
    };
});
