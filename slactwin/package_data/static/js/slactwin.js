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
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="parameterWithExternalLattice" data-parameter-with-lattice="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}" data-path-to-models="externalLattice"></div>
    `;
});

SIREPO.app.factory('slactwinService', function(appState, frameCache, persistentSimulation, $location, $rootScope) {
    const self = {};
    self.computeModel = analysisModel => 'animation';

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
            if (appState.models[m] && appState.models[m].archiveId) {
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

SIREPO.app.controller('SearchController', function(appState, requestSender, slactwinService, $scope) {
    const self = this;

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
                simulationId: SIREPO.nonSimulationId,
            },
        );
    };

    const init = () => {
        $scope.loadingMessage = "Loading archives";
        slactwinService.setArchiveId(null);
        appState.clearModels();
        appState.listSimulations((resp) => {
            $scope.simId = resp[0].simulationId;
            getSearchResults();
            self.isInitialized = true;
        });
    }

    $scope.openArchive = (row) => {
        requestSender.localRedirect(SIREPO.APP_SCHEMA.appModes.default.localRoute, {
            ':simulationId': $scope.simId,
        });
        slactwinService.setArchiveId(row.archiveId);
    };

    init();
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

SIREPO.app.directive('appHeader', function(authState, panelState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <ul class="nav navbar-nav" data-ng-if=":: authState.isLoggedIn">
              <li class="sim-section" data-ng-class="{active: nav.isActive('search')}"><a href data-ng-click="nav.openSection('search')"><span class="glyphicon glyphicon-search"></span> Search</a></li>
            </ul>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded>
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
