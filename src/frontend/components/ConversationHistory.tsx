import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Menu,
  Checkbox,
  ListItemText,
  CircularProgress,
  Tooltip,
  InputAdornment,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  MoreVert as MoreVertIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { useVirtualizer } from '@tanstack/react-virtual';
import { debounce } from 'lodash';
import { format, isAfter, isBefore, parseISO } from 'date-fns';

interface Message {
  role: string;
  content: string;
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  model: string;
  provider: string;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  starred: boolean;
  totalTokens: number;
  totalCost: number;
}

interface ConversationHistoryProps {
  conversations: Conversation[];
  onSelect: (conversationId: string) => void;
  onDelete: (conversationId: string) => void;
  onExport: (conversationIds: string[]) => void;
  onToggleStar: (conversationId: string) => void;
  onUpdateTags: (conversationId: string, tags: string[]) => void;
}

const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  conversations,
  onSelect,
  onDelete,
  onExport,
  onToggleStar,
  onUpdateTags,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModel, setSelectedModel] = useState<string>('all');
  const [selectedProvider, setSelectedProvider] = useState<string>('all');
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({
    start: '',
    end: '',
  });
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [showStarredOnly, setShowStarredOnly] = useState(false);
  const [selectedConversations, setSelectedConversations] = useState<string[]>([]);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [loading, setLoading] = useState(false);

  const parentRef = React.useRef<HTMLDivElement>(null);

  // Extract unique values for filters
  const availableModels = useMemo(
    () => Array.from(new Set(conversations.map((c) => c.model))),
    [conversations]
  );

  const availableProviders = useMemo(
    () => Array.from(new Set(conversations.map((c) => c.provider))),
    [conversations]
  );

  const availableTags = useMemo(
    () => Array.from(new Set(conversations.flatMap((c) => c.tags))),
    [conversations]
  );

  // Fuzzy search implementation
  const fuzzyMatch = (text: string, query: string): boolean => {
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    
    if (lowerText.includes(lowerQuery)) {
      return true;
    }

    // Simple fuzzy matching - check if query characters appear in order
    let queryIndex = 0;
    for (let i = 0; i < lowerText.length && queryIndex < lowerQuery.length; i++) {
      if (lowerText[i] === lowerQuery[queryIndex]) {
        queryIndex++;
      }
    }
    return queryIndex === lowerQuery.length;
  };

  // Filter conversations
  const filteredConversations = useMemo(() => {
    return conversations.filter((conv) => {
      // Search filter
      if (searchQuery) {
        const searchMatch =
          fuzzyMatch(conv.title, searchQuery) ||
          conv.messages.some((msg) => fuzzyMatch(msg.content, searchQuery));
        if (!searchMatch) return false;
      }

      // Model filter
      if (selectedModel !== 'all' && conv.model !== selectedModel) {
        return false;
      }

      // Provider filter
      if (selectedProvider !== 'all' && conv.provider !== selectedProvider) {
        return false;
      }

      // Tag filter
      if (selectedTags.length > 0) {
        const hasTag = selectedTags.some((tag) => conv.tags.includes(tag));
        if (!hasTag) return false;
      }

      // Date range filter
      if (dateRange.start) {
        const startDate = parseISO(dateRange.start);
        if (isBefore(parseISO(conv.createdAt), startDate)) {
          return false;
        }
      }
      if (dateRange.end) {
        const endDate = parseISO(dateRange.end);
        if (isAfter(parseISO(conv.createdAt), endDate)) {
          return false;
        }
      }

      // Starred filter
      if (showStarredOnly && !conv.starred) {
        return false;
      }

      return true;
    });
  }, [
    conversations,
    searchQuery,
    selectedModel,
    selectedProvider,
    selectedTags,
    dateRange,
    showStarredOnly,
  ]);

  // Virtual scrolling setup
  const rowVirtualizer = useVirtualizer({
    count: filteredConversations.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 120,
    overscan: 5,
  });

  // Debounced search
  const debouncedSearch = useMemo(
    () =>
      debounce((query: string) => {
        setSearchQuery(query);
      }, 300),
    []
  );

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    debouncedSearch(e.target.value);
  };

  const handleSelectConversation = (convId: string) => {
    setSelectedConversations((prev) =>
      prev.includes(convId)
        ? prev.filter((id) => id !== convId)
        : [...prev, convId]
    );
  };

  const handleExportSelected = () => {
    if (selectedConversations.length > 0) {
      onExport(selectedConversations);
      setSelectedConversations([]);
    }
  };

  const handleDeleteSelected = async () => {
    setLoading(true);
    for (const convId of selectedConversations) {
      await onDelete(convId);
    }
    setSelectedConversations([]);
    setLoading(false);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedModel('all');
    setSelectedProvider('all');
    setSelectedTags([]);
    setDateRange({ start: '', end: '' });
    setShowStarredOnly(false);
  };

  // Statistics
  const stats = useMemo(() => {
    return {
      total: conversations.length,
      filtered: filteredConversations.length,
      starred: conversations.filter((c) => c.starred).length,
      totalTokens: conversations.reduce((sum, c) => sum + c.totalTokens, 0),
      totalCost: conversations.reduce((sum, c) => sum + c.totalCost, 0),
    };
  }, [conversations, filteredConversations]);

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 2 }}>
      {/* Statistics Dashboard */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6">{stats.total}</Typography>
              <Typography color="text.secondary">Total Conversations</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6">{stats.starred}</Typography>
              <Typography color="text.secondary">Starred</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6">{stats.totalTokens.toLocaleString()}</Typography>
              <Typography color="text.secondary">Total Tokens</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6">${stats.totalCost.toFixed(2)}</Typography>
              <Typography color="text.secondary">Total Cost</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Search and Filters */}
      <Box sx={{ mb: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              placeholder="Search conversations..."
              onChange={handleSearchChange}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Model</InputLabel>
              <Select
                value={selectedModel}
                label="Model"
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                <MenuItem value="all">All Models</MenuItem>
                {availableModels.map((model) => (
                  <MenuItem key={model} value={model}>
                    {model}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <FormControl fullWidth>
              <InputLabel>Provider</InputLabel>
              <Select
                value={selectedProvider}
                label="Provider"
                onChange={(e) => setSelectedProvider(e.target.value)}
              >
                <MenuItem value="all">All Providers</MenuItem>
                {availableProviders.map((provider) => (
                  <MenuItem key={provider} value={provider}>
                    {provider}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Toggle starred only">
                <IconButton
                  onClick={() => setShowStarredOnly(!showStarredOnly)}
                  color={showStarredOnly ? 'primary' : 'default'}
                >
                  {showStarredOnly ? <StarIcon /> : <StarBorderIcon />}
                </IconButton>
              </Tooltip>
              <Tooltip title="Clear filters">
                <IconButton onClick={clearFilters}>
                  <CloseIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* Selected Actions */}
      {selectedConversations.length > 0 && (
        <Box sx={{ mb: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
          <Typography variant="body2">
            {selectedConversations.length} selected
          </Typography>
          <Button
            size="small"
            startIcon={<DownloadIcon />}
            onClick={handleExportSelected}
          >
            Export
          </Button>
          <Button
            size="small"
            startIcon={<DeleteIcon />}
            onClick={handleDeleteSelected}
            disabled={loading}
          >
            Delete
          </Button>
        </Box>
      )}

      {/* Conversation List with Virtual Scrolling */}
      <Box
        ref={parentRef}
        sx={{
          flex: 1,
          overflow: 'auto',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
        }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const conversation = filteredConversations[virtualRow.index];
            return (
              <Card
                key={conversation.id}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                sx={{ m: 1, cursor: 'pointer' }}
                onClick={() => onSelect(conversation.id)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Checkbox
                      checked={selectedConversations.includes(conversation.id)}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectConversation(conversation.id);
                      }}
                    />
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="h6">{conversation.title}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {format(parseISO(conversation.updatedAt), 'PPpp')}
                      </Typography>
                      <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        <Chip label={conversation.model} size="small" />
                        <Chip label={conversation.provider} size="small" />
                        {conversation.tags.map((tag) => (
                          <Chip key={tag} label={tag} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </Box>
                    <IconButton
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleStar(conversation.id);
                      }}
                    >
                      {conversation.starred ? <StarIcon color="primary" /> : <StarBorderIcon />}
                    </IconButton>
                  </Box>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </Box>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
          <CircularProgress />
        </Box>
      )}
    </Box>
  );
};

export default ConversationHistory;
